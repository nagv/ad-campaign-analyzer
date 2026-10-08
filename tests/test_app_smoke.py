"""End-to-end smoke tests of app.py with Streamlit's AppTest (no browser, no network)."""
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import ROOT
from src.views.common import EMPTY_MESSAGE

APP = str(ROOT / "app.py")


def apply(app):
    next(b for b in app.button if b.label == "Apply filters").click().run()
    assert not app.exception, app.exception


def reset(app):
    next(b for b in app.button if b.label == "Reset").click().run()


@pytest.fixture
def at(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    return app


def test_all_tabs_render(at):
    assert [t.label for t in at.tabs] == ["Overview", "Platform Comparison", "Campaign Details",
                                          "Time Series", "Ask the Data"]
    assert len(at.metric) == 8
    assert {m.label for m in at.metric} >= {"Spend ($)", "ROI (%)", "CPA ($)"}
    assert all(m.value.startswith("$") for m in at.metric if "($)" in m.label)
    assert len(at.dataframe) == 2  # platform + campaign tables
    assert any("OPENROUTER_API_KEY" in w.value for w in at.warning)  # assistant disabled hint


def test_empty_filters_show_friendly_message(at):
    at.multiselect(key="f_channels").set_value([])
    apply(at)
    assert sum(EMPTY_MESSAGE in i.value for i in at.info) == 4
    assert len(at.metric) == 0


def test_channel_filter_syncs_all_views(at):
    at.multiselect(key="f_channels").set_value(["Pinterest"])
    apply(at)
    assert any("Pinterest ·" in i.value for i in at.info)  # active-filter summary
    platform_table = at.dataframe[0].value
    assert list(platform_table["Channel"]) == ["Pinterest"]
    campaign_table = at.dataframe[1].value
    assert set(campaign_table["Channel"]) == {"Pinterest"}


def test_filters_wait_for_apply(at):
    at.multiselect(key="f_channels").set_value(["Twitter"]).run()  # changed but not applied
    assert len(at.dataframe[0].value) == 4
    at.multiselect(key="f_channels").set_value(["Twitter"])
    apply(at)
    assert list(at.dataframe[0].value["Channel"]) == ["Twitter"]


def test_custom_dates_and_reset(at):
    full = (at.date_input(key="f_start").value, at.date_input(key="f_end").value)
    at.date_input(key="f_start").set_value(date(2026, 6, 1))
    at.date_input(key="f_end").set_value(date(2026, 6, 30))
    apply(at)
    assert at.selectbox(key="f_preset").value == "Custom range"
    assert any("30 days" in c.value for c in at.caption)
    reset(at)
    assert (at.date_input(key="f_start").value, at.date_input(key="f_end").value) == full
    assert at.selectbox(key="f_preset").value == "All dates"
    assert len(at.multiselect(key="f_channels").value) == 4 and len(at.metric) == 8


def test_quick_range_preset(at):
    end = at.date_input(key="f_end").value
    at.selectbox(key="f_preset").set_value("Last 30 days")
    apply(at)
    assert at.date_input(key="f_end").value == end
    assert (end - at.date_input(key="f_start").value).days == 29
    assert any("(30 days)" in i.value for i in at.info)


def test_reversed_dates_are_swapped(at):
    at.date_input(key="f_start").set_value(date(2026, 7, 31))
    at.date_input(key="f_end").set_value(date(2026, 7, 1))
    apply(at)
    assert any("swapped" in w.value for w in at.warning)
    assert any("(31 days)" in i.value for i in at.info)


def test_partial_period_shows_deltas(at):
    at.selectbox(key="f_preset").set_value("Last 30 days")
    apply(at)
    assert any(m.delta and "vs prev. period" in m.delta for m in at.metric)


def test_campaign_search(at):
    at.text_input(key="campaign_search").set_value("pinterest").run()
    assert set(at.dataframe[1].value["Channel"]) == {"Pinterest"}
    at.text_input(key="campaign_search").set_value("zzz-nothing").run()
    assert any("No campaigns match" in i.value for i in at.info)


def test_time_series_controls(at):
    at.selectbox(key="ts_metric").set_value("ROI").run()
    at.radio(key="ts_freq").set_value("Monthly").run()
    at.toggle(key="ts_split").set_value(False).run()
    at.checkbox(key="ts_smooth").set_value(True).run()
    assert not at.exception


def test_platform_metric_selector(at):
    at.selectbox(key="plat_metric").set_value("ROAS").run()
    assert not at.exception


def test_assistant_answers_with_mocked_agent(monkeypatch):
    import src.agent.graph as graph

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    seen = {}

    def fake_ask(agent, history, question):
        seen["question"] = question
        return "Pinterest has the best ROI."

    monkeypatch.setattr(graph, "build_agent", lambda df, context, model=None: object())
    monkeypatch.setattr(graph, "ask", fake_ask)
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    app.chat_input[0].set_value("Which channel has the best ROI?").run()
    assert not app.exception
    assert seen["question"] == "Which channel has the best ROI?"
    assert any("Pinterest has the best ROI." in m.value for m in app.markdown)
    assert len(app.session_state["chat_history"]) == 2


def test_assistant_reports_errors(monkeypatch):
    import src.agent.graph as graph

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    def boom(*a, **k):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(graph, "build_agent", boom)
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    app.chat_input[0].set_value("hi").run()
    assert not app.exception
    assert any("quota exceeded" in m.value for m in app.markdown)
