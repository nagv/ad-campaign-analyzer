"""LangChain tool-calling agent over the filtered campaign data."""
from __future__ import annotations

import pandas as pd

from src.agent.tools import build_tools

SYSTEM_PROMPT = """You are a performance-marketing analyst inside an ad campaign dashboard.
The data covers Facebook, Instagram, Pinterest and Twitter campaigns, already filtered
to the marketer's current selection ({context}).

Rules:
- Always call a tool to get numbers. Never invent or estimate figures.
- Quote numbers with their units exactly as tools return them ($, %, ×).
- ROI = (Revenue - Spend) / Spend. Lower CPA and CPC are better.
- Lead with the direct answer, then 2-4 short bullet points of evidence.
- End with one concrete, actionable recommendation when it is relevant.
- If the data cannot answer the question, say so and suggest which filter to change."""


def build_agent(df: pd.DataFrame, context: str, model=None):
    from langchain.agents import create_agent

    if model is None:
        from src.agent.llm import get_llm
        model = get_llm()
    return create_agent(model=model, tools=build_tools(df),
                        system_prompt=SYSTEM_PROMPT.format(context=context))


def ask(agent, history: list[dict], question: str) -> str:
    """Run one turn. `history` holds prior {"role", "content"} messages."""
    messages = [*history, {"role": "user", "content": question}]
    result = agent.invoke({"messages": messages})
    content = result["messages"][-1].content
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return content
