"""Shared filters: one FilterState drives every view."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

import pandas as pd

FILTER_KEYS = ("f_preset", "f_start", "f_end", "f_channels", "f_audiences", "f_goals")


@dataclass(frozen=True)
class FilterState:
    start: date
    end: date
    channels: tuple = field(default_factory=tuple)
    audiences: tuple = field(default_factory=tuple)
    goals: tuple = field(default_factory=tuple)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def previous_period(self) -> "FilterState":
        """Same filters over the equally long window right before this one."""
        prev_end = self.start - timedelta(days=1)
        return replace(self, start=prev_end - timedelta(days=self.days - 1), end=prev_end)


def options(df: pd.DataFrame) -> dict:
    return {
        "channels": sorted(df["Channel"].dropna().unique().tolist()),
        "audiences": sorted(df["Target_Audience"].dropna().unique().tolist()),
        "goals": sorted(df["Campaign_Goal"].dropna().unique().tolist()),
        "min_date": df["Date"].min().date(),
        "max_date": df["Date"].max().date(),
    }


def default_state(df: pd.DataFrame) -> FilterState:
    o = options(df)
    return FilterState(o["min_date"], o["max_date"], tuple(o["channels"]),
                       tuple(o["audiences"]), tuple(o["goals"]))


def clamp_dates(start: date, end: date, min_date: date, max_date: date) -> tuple[date, date]:
    """Keep the range inside the data and in the right order."""
    if start > end:
        start, end = end, start
    start = min(max(start, min_date), max_date)
    end = max(min(end, max_date), min_date)
    return start, end


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    dates = df["Date"].dt.date
    mask = (
        (dates >= state.start)
        & (dates <= state.end)
        & df["Channel"].isin(state.channels)
        & df["Target_Audience"].isin(state.audiences)
        & df["Campaign_Goal"].isin(state.goals)
    )
    return df.loc[mask]


PRESETS = {
    "All dates": None,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Custom range": "custom",
}


def preset_range(preset: str, min_date: date, max_date: date) -> tuple[date, date] | None:
    """Dates for a quick-range preset, counted back from the latest date in the data.

    Returns None for "Custom range" (use the From/To pickers as they are).
    """
    days = PRESETS.get(preset)
    if days == "custom":
        return None
    if days is None:
        return min_date, max_date
    return max(min_date, max_date - timedelta(days=days - 1)), max_date


def default_widget_values(df: pd.DataFrame) -> dict:
    o = options(df)
    return {
        "f_preset": "All dates",
        "f_start": o["min_date"],
        "f_end": o["max_date"],
        "f_channels": o["channels"],
        "f_audiences": o["audiences"],
        "f_goals": o["goals"],
    }


def reset_filters(session_state, defaults: dict | None = None) -> None:
    """Restore filters. Assigning values (not just deleting keys) keeps the widgets in sync."""
    for key in FILTER_KEYS:
        if defaults:
            session_state[key] = defaults[key]
        else:
            session_state.pop(key, None)
    if defaults:
        session_state["f_applied_dates"] = (defaults["f_start"], defaults["f_end"])
    else:
        session_state.pop("f_applied_dates", None)


def _apply_preset(session_state, min_date: date, max_date: date) -> None:
    """Form-submit callback: turn a preset into concrete From/To dates before the rerun.

    If the user edited From/To since the last apply, their dates win and the
    preset switches to "Custom range".
    """
    picked = (session_state.get("f_start"), session_state.get("f_end"))
    if picked != session_state.get("f_applied_dates", picked):
        session_state["f_preset"] = "Custom range"
    rng = preset_range(session_state.get("f_preset", "All dates"), min_date, max_date)
    if rng is not None:
        session_state["f_start"], session_state["f_end"] = rng
    session_state["f_applied_dates"] = (session_state["f_start"], session_state["f_end"])


def describe(state: FilterState, opts: dict) -> str:
    """One-line summary of the active filters, shown above the tabs."""
    def part(selected, available, noun):
        if len(selected) == len(available):
            return f"all {noun}"
        if not selected:
            return f"no {noun}"
        return ", ".join(selected) if len(selected) <= 2 else f"{len(selected)} of {len(available)} {noun}"

    return (f"{state.start:%b %d, %Y} – {state.end:%b %d, %Y} ({state.days} days) · "
            f"{part(state.channels, opts['channels'], 'channels')} · "
            f"{part(state.audiences, opts['audiences'], 'audiences')} · "
            f"{part(state.goals, opts['goals'], 'goals')}")


def sidebar_filters(df: pd.DataFrame, data_signature: str) -> FilterState:
    """Render the sidebar filter form and return the *applied* FilterState.

    Widgets live in an st.form, so nothing changes until "Apply filters" is pressed.
    """
    import streamlit as st

    o = options(df)
    defaults = default_widget_values(df)
    # First run or new data (e.g. an uploaded CSV): start from "everything selected".
    if st.session_state.get("f_data_sig") != data_signature:
        reset_filters(st.session_state, defaults)
        st.session_state["f_data_sig"] = data_signature

    with st.sidebar.form("filters", border=False):
        st.header("Filters")
        st.selectbox("Quick range", list(PRESETS), key="f_preset",
                     help="Counted back from the latest date in the data. "
                          "Pick “Custom range” to use the From/To dates below.")
        c1, c2 = st.columns(2)
        c1.date_input("From", min_value=o["min_date"], max_value=o["max_date"], key="f_start",
                      format="YYYY-MM-DD")
        c2.date_input("To", min_value=o["min_date"], max_value=o["max_date"], key="f_end",
                      format="YYYY-MM-DD")
        st.multiselect("Channel", o["channels"], key="f_channels")
        st.multiselect("Target audience", o["audiences"], key="f_audiences")
        st.multiselect("Campaign goal", o["goals"], key="f_goals")

        a, b = st.columns(2)
        a.form_submit_button("Apply filters", type="primary", width="stretch",
                             on_click=_apply_preset, args=(st.session_state, o["min_date"], o["max_date"]))
        b.form_submit_button("Reset", width="stretch",
                             on_click=reset_filters, args=(st.session_state, defaults))

    ss = st.session_state
    start, end = ss["f_start"], ss["f_end"]
    if start > end:
        st.sidebar.warning("“From” is after “To”, so the dates were swapped.", icon="↔️")
    start, end = clamp_dates(start, end, o["min_date"], o["max_date"])
    return FilterState(start, end, tuple(ss["f_channels"]), tuple(ss["f_audiences"]), tuple(ss["f_goals"]))
