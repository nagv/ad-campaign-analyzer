"""Campaign details: searchable, sortable campaign-level table."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import metrics
from src.views.common import is_empty
from src.views.platform import TABLE_CONFIG

COLUMN_CONFIG = {
    "Campaign_ID": st.column_config.TextColumn("ID"),
    "Campaign_Name": st.column_config.TextColumn("Campaign"),
    "Target_Audience": st.column_config.TextColumn("Audience"),
    "Campaign_Goal": st.column_config.TextColumn("Goal"),
    "Start": st.column_config.DateColumn("Start", format="YYYY-MM-DD"),
    "End": st.column_config.DateColumn("End", format="YYYY-MM-DD"),
    **{k: v for k, v in TABLE_CONFIG.items() if k != "Spend_Share"},
}


def search(table: pd.DataFrame, query: str) -> pd.DataFrame:
    """Case-insensitive match on campaign name, ID, channel, audience or goal."""
    q = (query or "").strip().lower()
    if not q:
        return table
    haystack = table[["Campaign_ID", "Campaign_Name", "Channel", "Target_Audience", "Campaign_Goal"]]
    mask = haystack.apply(lambda col: col.str.lower().str.contains(q, regex=False)).any(axis=1)
    return table[mask]


def render(df: pd.DataFrame) -> None:
    st.subheader("Campaign details")
    if is_empty(df):
        return

    table = metrics.by_campaign(df)
    query = st.text_input("Search campaigns", placeholder="Name, ID, channel, audience or goal…",
                          key="campaign_search")
    result = search(table, query)
    if result.empty:
        st.info(f"No campaigns match “{query}”. Try a shorter search term.", icon="🔍")
        return

    st.caption(f"{len(result)} of {len(table)} campaigns · click a column header to sort.")
    st.dataframe(result[list(COLUMN_CONFIG)], column_config=COLUMN_CONFIG, hide_index=True,
                 width="stretch", height=min(38 * (len(result) + 1) + 4, 560))
    st.download_button(
        "Download table (CSV)",
        result.to_csv(index=False).encode("utf-8"),
        file_name="campaign_details.csv",
        mime="text/csv",
        key="campaign_download",
    )
