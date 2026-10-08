# Ad Campaign Performance Analyzer

A Streamlit dashboard that shows marketers which campaigns and channels deliver results. It compares **spend, clicks, conversions and ROI** across **Facebook, Instagram, Pinterest and Twitter** from a campaign CSV. It includes a LangChain agent you can ask questions in plain English.

## Views
| Tab | What you get |
|-----|--------------|
| **Overview** | 8 KPI cards (Spend, Revenue, ROI, ROAS, Clicks, Conversions, CPA, CTR), each with a delta against the previous period, plus a spend vs conversions trend and a best/worst-ROI callout |
| **Platform Comparison** | Channel table, spend vs revenue, ROI, CPA and a selectable metric chart, plus an efficiency bubble chart (CPA vs ROI) |
| **Campaign Details** | Searchable, sortable campaign table with CSV download |
| **Time Series** | Any metric, daily/weekly/monthly, split by channel, with an optional rolling average |
| **Ask the Data** | LangChain agent with read-only analytics tools (needs an OpenRouter key) |

All tabs share the sidebar filters: **date range, channel, target audience and campaign goal**. Every metric shows its unit ($, %, ×). Filter choices with no matching data show a friendly message instead of empty charts.

## Quick start (local)
```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```
The app opens at http://localhost:8501 with sample data. To use your own file, upload it from the sidebar. You can regenerate the sample data with `python scripts/generate_sample_data.py --seed 42`.

### Enable the assistant
Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`. You can optionally set `LLM_MODEL`; the default is `google/gemini-2.5-flash`.

## CSV format
Required columns. Matching ignores case and spacing, and common aliases such as `Platform`, `Cost` and `Objective` are accepted.

`Date, Campaign_ID, Campaign_Name, Channel, Target_Audience, Campaign_Goal, Spend, Impressions, Clicks, Conversions, Revenue`

Derived metrics are always computed from summed totals, never by averaging row-level ratios:

| Metric | Formula |
|--------|---------|
| CTR | Clicks / Impressions |
| CPC | Spend / Clicks |
| Conversion rate | Conversions / Clicks |
| CPA | Spend / Conversions |
| ROAS | Revenue / Spend |
| **ROI** | (Revenue − Spend) / Spend |

## Tests
```bash
pytest --cov=src
```
The suite has 50 tests: unit tests for data, metrics, filters, formatting and agent tools, plus Streamlit `AppTest` end-to-end checks for every tab, filter sync, empty states, search and the chat tab with a mocked LLM. None of the tests use the network.

## Docker
```bash
docker compose up --build                 # dashboard on http://localhost:8501
docker compose --profile test run --rm tests
```
`./data` is mounted into the container, and `.env` is loaded if it exists.

## Project layout
```
app.py                  entry point: data loading, sidebar filters, tabs
src/data.py             CSV schema validation, cleaning, derived metrics
src/metrics.py          KPIs, channel/campaign/time aggregations
src/filters.py          shared FilterState + sidebar controls
src/formatting.py       units and number formatting
src/views/              one module per tab
src/agent/              LangChain model, tools and agent
scripts/                sample data generator
docs/phase2_agent_proposal.md   roadmap for the AI agent
```
