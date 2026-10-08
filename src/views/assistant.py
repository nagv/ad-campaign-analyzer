"""Ask the Data: chat with a LangChain agent over the filtered data."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.agent.llm import has_api_key
from src.filters import FilterState
from src.views.common import is_empty

SUGGESTIONS = [
    "Which channel has the best ROI?",
    "What are my 3 worst campaigns by CPA?",
    "How have conversions trended week over week?",
    "Any unusual spend spikes I should check?",
]


def describe(state: FilterState) -> str:
    return (f"{state.start:%Y-%m-%d} to {state.end:%Y-%m-%d}; channels: {', '.join(state.channels)}; "
            f"{len(state.audiences)} audiences; {len(state.goals)} goals")


def render(df: pd.DataFrame, state: FilterState) -> None:
    st.subheader("Ask the data")
    st.caption("A LangChain agent answers questions using read-only tools over the filtered data.")

    if not has_api_key():
        st.warning(
            "Set `OPENROUTER_API_KEY` in a `.env` file (see `.env.example`) and restart the app "
            "to enable the assistant.",
            icon="🔑",
        )
        return
    if is_empty(df):
        return

    history = st.session_state.setdefault("chat_history", [])
    cols = st.columns(len(SUGGESTIONS))
    clicked = None
    for col, text in zip(cols, SUGGESTIONS):
        if col.button(text, width="stretch", key=f"suggest_{text}"):
            clicked = text

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask about spend, ROI, channels, campaigns…") or clicked
    if history and st.button("Clear conversation", key="chat_clear"):
        st.session_state["chat_history"] = []
        st.rerun()
    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Analysing…"):
            try:
                from src.agent.graph import ask, build_agent

                agent = build_agent(df, describe(state))
                answer = ask(agent, history[-8:], question)
            except Exception as exc:  # network / quota / provider errors
                answer = f"Sorry, the assistant could not answer right now: `{type(exc).__name__}: {exc}`"
        st.markdown(answer)
    history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
