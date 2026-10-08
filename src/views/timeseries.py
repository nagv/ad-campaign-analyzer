"""Time series: explore how a metric changes over time."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import metrics
from src.formatting import label
from src.views.common import CHANNEL_COLORS, axis_format, is_empty, plot


def render(df: pd.DataFrame) -> None:
    st.subheader("Time series")
    if is_empty(df):
        return

    c1, c2, c3 = st.columns([2, 2, 1.4])
    metric = c1.selectbox("Metric", metrics.ALL_METRICS, index=metrics.ALL_METRICS.index("Conversions"),
                          format_func=label, key="ts_metric")
    freq = c2.radio("Granularity", list(metrics.FREQ_MAP), index=1, horizontal=True, key="ts_freq")
    split = c3.toggle("Split by channel", value=True, key="ts_split")
    smooth = st.checkbox("Show 7-period rolling average", value=False, key="ts_smooth")

    ts = metrics.time_series(df, freq, split_by="Channel" if split else None)
    title = f"{label(metric)} — {freq.lower()}"
    if split:
        fig = px.line(ts, x="Date", y=metric, color="Channel", color_discrete_map=CHANNEL_COLORS,
                      markers=freq != "Daily", title=title)
        if smooth:
            for ch, part in ts.groupby("Channel"):
                fig.add_trace(go.Scatter(x=part["Date"], y=part[metric].rolling(7, min_periods=1).mean(),
                                         name=f"{ch} (7-pt avg)", mode="lines",
                                         line=dict(dash="dot", color=CHANNEL_COLORS.get(ch))))
    else:
        fig = px.line(ts, x="Date", y=metric, markers=freq != "Daily", title=title)
        if smooth:
            fig.add_trace(go.Scatter(x=ts["Date"], y=ts[metric].rolling(7, min_periods=1).mean(),
                                     name="7-pt avg", mode="lines", line=dict(dash="dot")))
    fig.update_layout(yaxis_title=label(metric), xaxis_title="")
    axis_format(fig, metric)
    plot(fig, height=440, key="ts_chart")

    if len(ts["Date"].unique()) < 2:
        st.caption("Only one period in the selection. Widen the date range or use a finer granularity.")
