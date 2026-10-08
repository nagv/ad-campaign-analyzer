import json

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.agent import tools as T
from src.agent.graph import SYSTEM_PROMPT, ask, build_agent


def test_kpis_summary(df):
    out = T.kpis_summary(df)
    assert out["Spend"] == "$450"
    assert out["ROI"] == "133.3%"
    assert out["campaigns"] == 3


def test_channel_comparison_ranks_by_metric(df):
    out = T.channel_comparison(df, "ROI")
    assert [c["Channel"] for c in out["channels"]] == ["Facebook", "Instagram"]
    out = T.channel_comparison(df, "Clicks")
    assert out["better_is"] == "higher" and "Clicks" in out["channels"][0]


def test_campaign_ranking_best_and_worst(df):
    assert T.campaign_ranking(df, "ROI", n=1)["campaigns"][0]["Campaign_ID"] == "C3"
    assert T.campaign_ranking(df, "ROI", n=1, worst=True)["campaigns"][0]["Campaign_ID"] == "C2"
    # C2 has no conversions, so it is excluded from CPA ranking.
    ids = [c["Campaign_ID"] for c in T.campaign_ranking(df, "CPA", n=10)["campaigns"]]
    assert ids == ["C1", "C3"]


def test_trend_summary(df):
    out = T.trend_summary(df, "Spend", "Daily")
    assert out["periods"] == 4
    assert out["peak_period"] == "2026-01-03"
    assert out["change_first_to_last"] == "-50.0%"


def test_anomalies_flags_spike(df):
    import pandas as pd

    days = pd.date_range("2026-02-01", periods=30)
    base = df.iloc[[0]].copy()
    spiky = pd.concat([base.assign(Date=d, Spend=1000 if i == 15 else 100) for i, d in enumerate(days)])
    out = T.anomalies(spiky, "Spend")
    assert out["count"] == 1 and out["anomalies"][0]["date"] == "2026-02-16"
    assert T.anomalies(df.iloc[[0]], "Spend")["count"] == 0  # zero variance


def test_tools_handle_empty_frame(df):
    empty = df.iloc[0:0]
    for fn in (T.kpis_summary, T.channel_comparison, T.campaign_ranking, T.trend_summary, T.anomalies):
        assert "error" in fn(empty)


def test_build_tools_are_bound_to_frame(df):
    tools = {t.name: t for t in T.build_tools(df)}
    assert set(tools) == {"get_kpis", "compare_channels", "top_campaigns", "trend", "find_anomalies"}
    assert json.loads(tools["get_kpis"].invoke({}))["Spend"] == "$450"
    assert json.loads(tools["compare_channels"].invoke({"metric": "CPA"}))["better_is"] == "lower"
    assert json.loads(tools["top_campaigns"].invoke({"metric": "ROI", "n": 2}))["order"] == "best"
    assert json.loads(tools["trend"].invoke({"metric": "Clicks", "freq": "Weekly"}))["granularity"] == "Weekly"
    assert "anomalies" in json.loads(tools["find_anomalies"].invoke({"metric": "Spend"}))


class ToolFakeModel(GenericFakeChatModel):
    """Fake chat model that accepts bind_tools (no network)."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_agent_calls_tool_then_answers(df):
    model = ToolFakeModel(messages=iter([
        AIMessage(content="", tool_calls=[{"name": "compare_channels", "args": {"metric": "ROI"}, "id": "t1"}]),
        AIMessage(content="Facebook has the best ROI at 300.0%."),
    ]))
    agent = build_agent(df, "test filters", model=model)
    answer = ask(agent, [], "Which channel has the best ROI?")
    assert "Facebook" in answer


def test_ask_flattens_content_blocks():
    class Stub:
        def invoke(self, payload):
            assert payload["messages"][-1] == {"role": "user", "content": "hi"}
            return {"messages": [AIMessage(content=[{"type": "text", "text": "a"}, "b"])]}

    assert ask(Stub(), [], "hi") == "ab"


def test_system_prompt_mentions_context():
    assert "{context}" in SYSTEM_PROMPT


def test_get_llm_uses_openrouter(monkeypatch):
    from src.agent import llm

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-4o-mini")
    model = llm.get_llm()
    assert llm.has_api_key()
    assert model.model_name == "openai/gpt-4o-mini"
    assert model.max_tokens == 1000
    assert "openrouter.ai" in str(model.openai_api_base)
    monkeypatch.delenv("OPENROUTER_API_KEY")
    assert not llm.has_api_key()
