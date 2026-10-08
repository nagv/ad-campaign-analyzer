from dataclasses import replace
from datetime import date

from src.filters import (FilterState, _apply_preset, apply_filters, clamp_dates, default_state, default_widget_values,
                         describe, options, preset_range, reset_filters)


def test_default_state_selects_everything(df):
    s = default_state(df)
    assert s.start == date(2026, 1, 1) and s.end == date(2026, 1, 4)
    assert len(apply_filters(df, s)) == len(df)


def test_options(df):
    o = options(df)
    assert o["channels"] == ["Facebook", "Instagram"]
    assert o["goals"] == ["Brand Awareness", "Increase Sales"]


def test_each_filter(df):
    s = default_state(df)
    assert set(apply_filters(df, replace(s, channels=("Facebook",)))["Channel"]) == {"Facebook"}
    assert len(apply_filters(df, replace(s, audiences=("Women 25-34",)))) == 1
    assert len(apply_filters(df, replace(s, goals=("Increase Sales",)))) == 3
    assert len(apply_filters(df, replace(s, start=date(2026, 1, 2), end=date(2026, 1, 3)))) == 2


def test_combined_filters_can_be_empty(df):
    s = replace(default_state(df), channels=("Facebook",), goals=("Brand Awareness",))
    assert apply_filters(df, s).empty
    assert apply_filters(df, replace(default_state(df), channels=())).empty


def test_previous_period():
    s = FilterState(date(2026, 1, 11), date(2026, 1, 20))
    p = s.previous_period()
    assert (p.start, p.end) == (date(2026, 1, 1), date(2026, 1, 10))
    assert p.days == s.days == 10


def test_clamp_dates():
    lo, hi = date(2026, 1, 1), date(2026, 1, 31)
    assert clamp_dates(date(2025, 12, 1), date(2026, 3, 1), lo, hi) == (lo, hi)
    assert clamp_dates(date(2026, 1, 20), date(2026, 1, 5), lo, hi) == (date(2026, 1, 5), date(2026, 1, 20))


def test_reset_filters_only_clears_filter_keys():
    state = {"f_channels": ["x"], "f_start": 1, "f_preset": "Last 7 days", "chat_history": [1]}
    reset_filters(state)
    assert state == {"chat_history": [1]}


def test_reset_filters_assigns_defaults(df):
    defaults = default_widget_values(df)
    state = {"f_channels": [], "f_start": date(2026, 1, 2), "f_preset": "Last 7 days"}
    reset_filters(state, defaults)
    assert state["f_channels"] == ["Facebook", "Instagram"]
    assert (state["f_start"], state["f_end"]) == (date(2026, 1, 1), date(2026, 1, 4))
    assert state["f_preset"] == "All dates"
    assert state["f_applied_dates"] == (date(2026, 1, 1), date(2026, 1, 4))


LO, HI = date(2026, 4, 1), date(2026, 9, 26)


def test_preset_range():
    assert preset_range("All dates", LO, HI) == (LO, HI)
    assert preset_range("Last 7 days", LO, HI) == (date(2026, 9, 20), HI)
    assert preset_range("Last 30 days", LO, HI) == (date(2026, 8, 28), HI)
    assert preset_range("Last 90 days", date(2026, 9, 1), HI) == (date(2026, 9, 1), HI)  # clamped
    assert preset_range("Custom range", LO, HI) is None


def test_apply_preset_sets_dates():
    state = {"f_preset": "Last 7 days", "f_start": LO, "f_end": HI, "f_applied_dates": (LO, HI)}
    _apply_preset(state, LO, HI)
    assert (state["f_start"], state["f_end"]) == (date(2026, 9, 20), HI)
    assert state["f_preset"] == "Last 7 days"


def test_apply_preset_manual_dates_win():
    june = (date(2026, 6, 1), date(2026, 6, 30))
    state = {"f_preset": "Last 7 days", "f_start": june[0], "f_end": june[1], "f_applied_dates": (LO, HI)}
    _apply_preset(state, LO, HI)
    assert (state["f_start"], state["f_end"]) == june
    assert state["f_preset"] == "Custom range"
    assert state["f_applied_dates"] == june


def test_describe(df):
    o = options(df)
    s = default_state(df)
    assert describe(s, o) == "Jan 01, 2026 – Jan 04, 2026 (4 days) · all channels · all audiences · all goals"
    s2 = replace(s, channels=("Facebook",), goals=())
    text = describe(s2, o)
    assert "Facebook ·" in text and "no goals" in text
