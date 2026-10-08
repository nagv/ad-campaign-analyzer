"""Ad Campaign Performance Analyzer — Streamlit entry point.

Run: streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import streamlit as st

from src.data import SchemaError, load_csv
from src.filters import apply_filters, describe, options, sidebar_filters
from src.views import assistant, campaigns, overview, platform, timeseries

SAMPLE_PATH = Path(__file__).parent / "data" / "sample_campaigns.csv"

st.set_page_config(page_title="Ad Campaign Performance Analyzer", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
    @media (max-width: 640px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }
        [data-testid="stMetricValue"] { font-size: 1.25rem; }
        [data-testid="stMetricLabel"] p { font-size: 0.8rem; }
        h1 { font-size: 1.6rem !important; }
        .stTabs [data-baseweb="tab"] { padding-left: 0.5rem; padding-right: 0.5rem; }
        .st-key-kpis [data-testid="stHorizontalBlock"] { flex-flow: row wrap !important; gap: 0.5rem; }
        .st-key-kpis [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.5rem) !important; min-width: calc(50% - 0.5rem) !important;
        }
        .st-key-kpis [data-testid="stMetric"] { padding: 0.5rem 0.6rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading campaign data…")
def load_bytes(data: bytes):
    return load_csv(io.BytesIO(data))


def sample_bytes() -> bytes:
    if not SAMPLE_PATH.exists():
        from scripts.generate_sample_data import generate

        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate().to_csv(SAMPLE_PATH, index=False)
    return SAMPLE_PATH.read_bytes()


st.title("📊 Ad Campaign Performance Analyzer")
st.caption("Compare spend, clicks, conversions and ROI across Facebook, Instagram, Pinterest and Twitter.")

with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Upload campaign CSV", type="csv",
                              help="Columns: Date, Campaign_ID, Campaign_Name, Channel, Target_Audience, "
                                   "Campaign_Goal, Spend, Impressions, Clicks, Conversions, Revenue")
    raw = upload.getvalue() if upload else sample_bytes()
    st.caption(f"Using **{upload.name if upload else 'sample data'}**")

try:
    df = load_bytes(raw)
except SchemaError as exc:
    st.error(str(exc), icon="⚠️")
    st.stop()
except Exception as exc:  # unreadable file
    st.error(f"Could not read this CSV: {exc}", icon="⚠️")
    st.stop()

if df.empty:
    st.warning("The CSV has no usable rows (check the Date column).", icon="⚠️")
    st.stop()

state = sidebar_filters(df, hashlib.md5(raw).hexdigest())
filtered = apply_filters(df, state)
previous = apply_filters(df, state.previous_period())

st.info(f"**Showing:** {describe(state, options(df))} · {len(filtered):,} rows", icon="🔎")

st.sidebar.divider()
st.sidebar.caption(f"{len(filtered):,} rows · {filtered['Campaign_ID'].nunique()} campaigns in view")

tabs = st.tabs(["Overview", "Platform Comparison", "Campaign Details", "Time Series", "Ask the Data"])
with tabs[0]:
    overview.render(filtered, previous, state.days)
with tabs[1]:
    platform.render(filtered)
with tabs[2]:
    campaigns.render(filtered)
with tabs[3]:
    timeseries.render(filtered)
with tabs[4]:
    assistant.render(filtered, state)
