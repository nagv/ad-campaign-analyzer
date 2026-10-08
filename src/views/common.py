"""Shared chart styling and empty-state handling for the views."""
from __future__ import annotations

import pandas as pd
import streamlit as st

CHANNEL_COLORS = {
    "Facebook": "#1877F2",
    "Instagram": "#E1306C",
    "Pinterest": "#BD081C",
    "Twitter": "#1DA1F2",
}

EMPTY_MESSAGE = (
    "No campaigns match these filters. Try widening the date range "
    "or adding channels, audiences or goals in the sidebar."
)


def is_empty(df: pd.DataFrame) -> bool:
    """Show the friendly empty state and return True when there is nothing to plot."""
    if df.empty:
        st.info(EMPTY_MESSAGE, icon="🔍")
        return True
    return False


def style(fig, height: int = 380):
    """Compact, mobile-friendly Plotly layout with the legend under the chart."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=40, b=8),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0, title_text=""),
        hovermode="x unified",
        title_font_size=15,
    )
    return fig


def axis_format(fig, metric: str):
    """Put the metric's unit on the y-axis ticks."""
    from src.formatting import CURRENCY, PERCENT, RATIO

    if metric in CURRENCY:
        fig.update_yaxes(tickprefix="$")
    elif metric in PERCENT:
        fig.update_yaxes(tickformat=".0%")
    elif metric in RATIO:
        fig.update_yaxes(ticksuffix="×")
    return fig


def plot(fig, height: int = 380, key: str | None = None):
    st.plotly_chart(style(fig, height), width="stretch", key=key,
                    config={"displaylogo": False, "responsive": True})
