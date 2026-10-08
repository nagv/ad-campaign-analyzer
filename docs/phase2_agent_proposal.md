# Phase 2 — LangChain Analytics Agent

## What ships today (MVP)
The **Ask the Data** tab runs a LangChain tool-calling agent (`langchain.agents.create_agent`) on OpenRouter (`google/gemini-2.5-flash` by default).

- **Grounded:** the agent can only call five read-only tools (`get_kpis`, `compare_channels`, `top_campaigns`, `trend`, `find_anomalies`). It cannot run code, so every number it gives comes from the same pandas logic the charts use.
- **Filter-aware:** the tools are bound to the frame *after* the sidebar filters are applied. "Best channel" means the best channel for the marketer's current selection.
- **Safe by default:** the system prompt bans invented numbers and requires units. Provider errors show as a friendly message, and the tab turns itself off when there's no API key.

Code: `src/agent/llm.py` (model), `src/agent/tools.py` (tools), `src/agent/graph.py` (agent), `src/views/assistant.py` (UI).

## Proposed next capabilities

| # | Idea | What it does | How (LangChain) | Value |
|---|------|--------------|-----------------|-------|
| 1 | **Insight narrator** | Writes an automatic "What changed this period" summary at the top of the Overview | One chain call over `get_kpis` + previous-period deltas + `find_anomalies`; output cached per filter state | Marketers get the story without having to read every chart |
| 2 | **Budget reallocation advisor** | Suggests how to move spend from low-ROI to high-ROI channels and campaigns, with a what-if forecast | New `simulate_reallocation(shifts)` tool using per-channel marginal ROAS; structured output (`with_structured_output`) → a table the UI renders | Turns analysis into a decision |
| 3 | **Natural-language filters** | "Show Instagram, women 25-34, last 30 days" sets the sidebar | Structured output → `FilterState`, which then writes `st.session_state` keys | Faster exploration on mobile |
| 4 | **Anomaly alerts** | A nightly job scans for spend spikes or conversion drops and drafts an alert | Scheduled script runs the same tools headless; a human approves before any message goes out | Catches wasted spend early |
| 5 | **Creative & copy assistant** | For under-performing campaigns, drafts new ad copy variants per channel and audience | Prompt template with campaign context (goal, audience, CTR vs channel average) | Closes the loop from insight to action |
| 6 | **Weekly report writer** | Produces a shareable PDF/Markdown report with charts and commentary | Multi-step chain: KPIs → channel compare → top/bottom campaigns → narrative | Saves analyst hours |
| 7 | **Multi-agent split** | An *Analyst* agent (data tools) hands findings to a *Strategist* agent (recommendations) | LangGraph supervisor with two sub-agents and shared state | Clearer reasoning, easier evaluation |

## Guardrails
- Read-only tools only. Any action with side effects (sending alerts, changing budgets) needs explicit human approval through LangGraph `interrupt`.
- Tool outputs are capped (top-N, last 12 periods) to keep prompts small and cheap. `max_tokens` is always set.
- Every answer must cite tool numbers. A post-check can compare the numbers in the answer against the tool outputs.
- No PII in the CSV is sent to the model beyond campaign-level aggregates.

## Evaluation plan
- **Golden questions:** about 30 questions with known answers computed from the sample CSV (e.g. "best ROI channel" → Pinterest). Run them in CI with a cheap model and check accuracy.
- **Grounding check:** every number in an answer must appear in some tool output from that run.
- **Tool-choice accuracy:** use LangSmith traces to check that the right tool was called with sensible arguments.
- **Cost and latency budget:** track tokens per answer, with a target of under 3 s p50.
