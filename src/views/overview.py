"""Overview: headline KPIs and spend vs conversions trend."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import metrics
from src.formatting import fmt_metric, label
from src.views.common import is_empty, plot

KPI_ROWS = [["Spend", "Revenue", "ROI", "ROAS"], ["Clicks", "Conversions", "CPA", "CTR"]]


def _delta(metric: str, current: float, previous: float | None):
    change = metrics.pct_change(current, previous)
    if change is None:
        return None
    return f"{change * 100:+.1f}% vs prev. period"


def render(df: pd.DataFrame, prev_df: pd.DataFrame, period_days: int) -> None:
    st.subheader("Overview")
    if is_empty(df):
        return

    current = metrics.kpis(df)
    previous = metrics.kpis(prev_df) if not prev_df.empty else {}
    st.caption(f"Selected period: {period_days} days · deltas compare with the {period_days} days before it.")

    # The "kpis" key gives the container a CSS class; app.py turns it into a 2-up grid on phones.
    with st.container(key="kpis"):
        for row in KPI_ROWS:
            cols = st.columns(len(row))
            for col, m in zip(cols, row):
                col.metric(
                    label(m),
                    fmt_metric(m, current[m]),
                    delta=_delta(m, current[m], previous.get(m)),
                    delta_color="inverse" if m in metrics.LOWER_IS_BETTER else "normal",
                    border=True,
                )

    freq = "Daily" if period_days <= 31 else "Weekly"
    ts = metrics.time_series(df, freq)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=ts["Date"], y=ts["Spend"], name="Spend ($)", marker_color="#94A3B8",
                         hovertemplate="$%{y:,.0f}"), secondary_y=False)
    fig.add_trace(go.Scatter(x=ts["Date"], y=ts["Conversions"], name="Conversions", mode="lines+markers",
                             line=dict(color="#16A34A", width=3), hovertemplate="%{y:,.0f}"),
                  secondary_y=True)
    fig.update_layout(title=f"Spend vs conversions ({freq.lower()})")
    fig.update_yaxes(title_text="Spend ($)", tickprefix="$", rangemode="tozero", secondary_y=False)
    fig.update_yaxes(title_text="Conversions", rangemode="tozero", secondary_y=True, showgrid=False)
    plot(fig, height=400, key="overview_trend")

    by_ch = metrics.by_channel(df)
    best = metrics.best_and_worst(by_ch, "ROI")
    if best and len(by_ch) > 1:
        st.success(
            f"**{best[0]}** delivers the best ROI ({fmt_metric('ROI', best[1])}); "
            f"**{best[2]}** the lowest ({fmt_metric('ROI', best[3])}).",
            icon="🏆",
        )
