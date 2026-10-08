"""Platform comparison across advertising channels."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src import metrics
from src.formatting import fmt_metric, label
from src.views.common import CHANNEL_COLORS, axis_format, is_empty, plot

TABLE_CONFIG = {
    "Channel": st.column_config.TextColumn("Channel"),
    "Spend": st.column_config.NumberColumn("Spend ($)", format="dollar"),
    "Spend_Share": st.column_config.ProgressColumn("Share of spend", format="percent", min_value=0, max_value=1),
    "Impressions": st.column_config.NumberColumn("Impressions", format="localized"),
    "Clicks": st.column_config.NumberColumn("Clicks", format="localized"),
    "Conversions": st.column_config.NumberColumn("Conversions", format="localized"),
    "Revenue": st.column_config.NumberColumn("Revenue ($)", format="dollar"),
    "CTR": st.column_config.NumberColumn("CTR (%)", format="percent"),
    "CVR": st.column_config.NumberColumn("Conv. rate (%)", format="percent"),
    "CPC": st.column_config.NumberColumn("CPC ($)", format="dollar"),
    "CPA": st.column_config.NumberColumn("CPA ($)", format="dollar"),
    "ROAS": st.column_config.NumberColumn("ROAS (×)", format="%.2f×"),
    "ROI": st.column_config.NumberColumn("ROI (%)", format="percent"),
}


def _bar(table: pd.DataFrame, metric: str, key: str):
    fig = px.bar(table, x="Channel", y=metric, color="Channel", color_discrete_map=CHANNEL_COLORS,
                 title=label(metric), text=table[metric].map(lambda v: fmt_metric(metric, v)))
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{text}")
    fig.update_layout(showlegend=False, yaxis_title=label(metric), xaxis_title="", hovermode="closest")
    axis_format(fig, metric)
    plot(fig, height=320, key=key)


def render(df: pd.DataFrame) -> None:
    st.subheader("Platform comparison")
    if is_empty(df):
        return

    table = metrics.by_channel(df)
    st.dataframe(table[list(TABLE_CONFIG)], column_config=TABLE_CONFIG, hide_index=True,
                 width="stretch")

    left, right = st.columns(2)
    with left:
        long = table.melt(id_vars="Channel", value_vars=["Spend", "Revenue"], var_name="Metric", value_name="USD")
        fig = px.bar(long, x="Channel", y="USD", color="Metric", barmode="group",
                     title="Spend vs revenue ($)", color_discrete_sequence=["#94A3B8", "#16A34A"])
        fig.update_layout(yaxis_tickprefix="$", xaxis_title="", hovermode="closest")
        plot(fig, height=320, key="plat_spend_rev")
    with right:
        _bar(table, "ROI", key="plat_roi")

    left, right = st.columns(2)
    with left:
        _bar(table, "CPA", key="plat_cpa")
    with right:
        choices = [m for m in metrics.ALL_METRICS if m not in {"ROI", "CPA"}]
        metric = st.selectbox("Compare another metric", choices, index=choices.index("Conversions"),
                              format_func=label, key="plat_metric")
        _bar(table, metric, key="plat_custom")

    fig = px.scatter(table, x="CPA", y="ROI", size="Spend", color="Channel", text="Channel",
                     color_discrete_map=CHANNEL_COLORS, size_max=60,
                     title="Efficiency: CPA vs ROI (bubble size = spend)")
    fig.update_traces(textposition="top center", cliponaxis=False)
    roi = table["ROI"].dropna()
    pad = max((roi.max() - roi.min()) * 0.25, 0.1) if not roi.empty else 0.1
    fig.update_layout(xaxis_title="CPA ($)", yaxis_title="ROI (%)", xaxis_tickprefix="$",
                      yaxis_tickformat=".0%", hovermode="closest", showlegend=False)
    if not roi.empty:
        fig.update_yaxes(range=[roi.min() - pad, roi.max() + pad])
    plot(fig, height=380, key="plat_scatter")
    st.caption("Top-left is best: cheap conversions with high return.")
