"""Read-only analytics tools the agent can call.

Tools close over the dashboard's *filtered* frame, so answers always match
what the marketer sees. The agent cannot run arbitrary code.
"""
from __future__ import annotations

import json
from typing import Literal

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from src import metrics
from src.formatting import fmt_metric

Metric = Literal["Spend", "Impressions", "Clicks", "Conversions", "Revenue",
                 "CTR", "CPC", "CVR", "CPA", "ROAS", "ROI"]
Freq = Literal["Daily", "Weekly", "Monthly"]


def _fmt_record(record: dict) -> dict:
    return {k: (fmt_metric(k, v) if k in metrics.ALL_METRICS or k == "Spend_Share" else v)
            for k, v in record.items()}


def kpis_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"error": "No data for the current filters."}
    k = metrics.kpis(df)
    return {
        "period": f"{df['Date'].min():%Y-%m-%d} to {df['Date'].max():%Y-%m-%d}",
        "campaigns": int(df["Campaign_ID"].nunique()),
        **{m: fmt_metric(m, v) for m, v in k.items()},
    }


def channel_comparison(df: pd.DataFrame, metric: str = "ROI") -> dict:
    if df.empty:
        return {"error": "No data for the current filters."}
    table = metrics.by_channel(df)
    ascending = metric in metrics.LOWER_IS_BETTER
    table = table.sort_values(metric, ascending=ascending, na_position="last")
    cols = ["Channel", "Spend", "Conversions", "Revenue", "CPA", "ROAS", "ROI", "Spend_Share"]
    if metric not in cols:
        cols.insert(1, metric)
    return {
        "ranked_by": metric,
        "better_is": "lower" if ascending else "higher",
        "channels": [_fmt_record(r) for r in table[cols].to_dict("records")],
    }


def campaign_ranking(df: pd.DataFrame, metric: str = "ROI", n: int = 5, worst: bool = False) -> dict:
    if df.empty:
        return {"error": "No data for the current filters."}
    table = metrics.by_campaign(df).dropna(subset=[metric])
    ascending = (metric in metrics.LOWER_IS_BETTER) != worst
    table = table.sort_values(metric, ascending=ascending).head(max(1, min(n, 25)))
    cols = ["Campaign_Name", "Campaign_ID", "Channel", "Campaign_Goal", "Spend", "Conversions", "CPA", "ROI"]
    if metric not in cols:
        cols.append(metric)
    return {"metric": metric, "order": "worst" if worst else "best",
            "campaigns": [_fmt_record(r) for r in table[cols].to_dict("records")]}


def trend_summary(df: pd.DataFrame, metric: str = "Conversions", freq: str = "Weekly") -> dict:
    if df.empty:
        return {"error": "No data for the current filters."}
    ts = metrics.time_series(df, freq)
    values = ts[metric].astype(float)
    first, last = values.iloc[0], values.iloc[-1]
    change = metrics.pct_change(last, first)
    peak = ts.loc[values.idxmax()] if values.notna().any() else None
    return {
        "metric": metric,
        "granularity": freq,
        "periods": int(len(ts)),
        "first_period": fmt_metric(metric, first),
        "last_period": fmt_metric(metric, last),
        "change_first_to_last": None if change is None else f"{change * 100:+.1f}%",
        "peak_period": None if peak is None else f"{peak['Date']:%Y-%m-%d}",
        "peak_value": None if peak is None else fmt_metric(metric, peak[metric]),
        "series": [{"period": f"{d:%Y-%m-%d}", metric: fmt_metric(metric, v)}
                   for d, v in zip(ts["Date"].tail(12), values.tail(12))],
    }


def anomalies(df: pd.DataFrame, metric: str = "Spend", threshold: float = 2.5) -> dict:
    """Days where the daily total is more than `threshold` std devs from the mean."""
    if df.empty:
        return {"error": "No data for the current filters."}
    ts = metrics.time_series(df, "Daily", split_by="Channel")
    found = []
    for ch, part in ts.groupby("Channel"):
        vals = part[metric].astype(float)
        std = vals.std(ddof=0)
        if not std or np.isnan(std):
            continue
        z = (vals - vals.mean()) / std
        for idx in z[z.abs() >= threshold].index:
            found.append({
                "date": f"{part.at[idx, 'Date']:%Y-%m-%d}",
                "channel": ch,
                metric: fmt_metric(metric, vals[idx]),
                "typical": fmt_metric(metric, vals.mean()),
                "z_score": round(float(z[idx]), 2),
            })
    found.sort(key=lambda r: abs(r["z_score"]), reverse=True)
    return {"metric": metric, "threshold_z": threshold, "count": len(found), "anomalies": found[:15]}


def build_tools(df: pd.DataFrame) -> list:
    """LangChain tools bound to the currently filtered frame."""

    @tool
    def get_kpis() -> str:
        """Headline KPIs (spend, revenue, ROI, ROAS, CPA, CTR, conversions...) for the current filters."""
        return json.dumps(kpis_summary(df))

    @tool
    def compare_channels(metric: Metric = "ROI") -> str:
        """Compare Facebook, Instagram, Pinterest and Twitter, ranked best-first by `metric`."""
        return json.dumps(channel_comparison(df, metric))

    @tool
    def top_campaigns(metric: Metric = "ROI", n: int = 5, worst: bool = False) -> str:
        """Best (or worst, if worst=True) n campaigns by `metric`."""
        return json.dumps(campaign_ranking(df, metric, n, worst))

    @tool
    def trend(metric: Metric = "Conversions", freq: Freq = "Weekly") -> str:
        """How `metric` changes over time at Daily/Weekly/Monthly granularity."""
        return json.dumps(trend_summary(df, metric, freq))

    @tool
    def find_anomalies(metric: Metric = "Spend") -> str:
        """Unusual daily spikes or drops in `metric`, per channel (z-score >= 2.5)."""
        return json.dumps(anomalies(df, metric))

    return [get_kpis, compare_channels, top_campaigns, trend, find_anomalies]
