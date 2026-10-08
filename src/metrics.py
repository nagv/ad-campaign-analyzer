"""Aggregations. Ratios are always recomputed from summed totals."""
from __future__ import annotations

import pandas as pd

from src.data import safe_div

SUM_COLUMNS = ["Spend", "Impressions", "Clicks", "Conversions", "Revenue"]
RATIO_COLUMNS = ["CTR", "CPC", "CVR", "CPA", "ROAS", "ROI"]
ALL_METRICS = SUM_COLUMNS + RATIO_COLUMNS

# Metrics where a lower value is better (used for best/worst callouts).
LOWER_IS_BETTER = {"CPC", "CPA"}

FREQ_MAP = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}


def _with_ratios(agg: pd.DataFrame) -> pd.DataFrame:
    agg = agg.copy()
    agg["CTR"] = safe_div(agg["Clicks"], agg["Impressions"])
    agg["CPC"] = safe_div(agg["Spend"], agg["Clicks"])
    agg["CVR"] = safe_div(agg["Conversions"], agg["Clicks"])
    agg["CPA"] = safe_div(agg["Spend"], agg["Conversions"])
    agg["ROAS"] = safe_div(agg["Revenue"], agg["Spend"])
    agg["ROI"] = safe_div(agg["Revenue"] - agg["Spend"], agg["Spend"])
    return agg


def kpis(df: pd.DataFrame) -> dict:
    """Headline totals and ratios for a (filtered) frame."""
    totals = df[SUM_COLUMNS].sum()
    row = _with_ratios(totals.to_frame().T).iloc[0]
    return {k: float(row[k]) for k in ALL_METRICS}


def pct_change(current: float, previous: float):
    """Relative change, or None when there is no meaningful baseline."""
    if previous is None or pd.isna(previous) or previous == 0 or pd.isna(current):
        return None
    return (current - previous) / abs(previous)


def by_channel(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("Channel", as_index=False)[SUM_COLUMNS].sum()
    agg = _with_ratios(agg)
    agg["Spend_Share"] = safe_div(agg["Spend"], agg["Spend"].sum())
    return agg.sort_values("Spend", ascending=False).reset_index(drop=True)


def by_campaign(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["Campaign_ID", "Campaign_Name", "Channel", "Target_Audience", "Campaign_Goal"]
    agg = df.groupby(keys, as_index=False).agg(
        **{c: (c, "sum") for c in SUM_COLUMNS},
        Start=("Date", "min"),
        End=("Date", "max"),
    )
    agg = _with_ratios(agg)
    return agg.sort_values("Spend", ascending=False).reset_index(drop=True)


def time_series(df: pd.DataFrame, freq: str = "Weekly", split_by: str | None = None) -> pd.DataFrame:
    """Resample totals by period (Daily/Weekly/Monthly), optionally per Channel."""
    rule = FREQ_MAP.get(freq, freq)
    keys = [pd.Grouper(key="Date", freq=rule, label="left", closed="left")]
    if split_by:
        keys.append(split_by)
    agg = df.groupby(keys)[SUM_COLUMNS].sum().reset_index()
    return _with_ratios(agg)


def best_and_worst(table: pd.DataFrame, metric: str, label_col: str = "Channel"):
    """Return (best_label, best_value, worst_label, worst_value) for a metric."""
    valid = table.dropna(subset=[metric])
    if valid.empty:
        return None
    ascending = metric in LOWER_IS_BETTER
    ordered = valid.sort_values(metric, ascending=ascending)
    best, worst = ordered.iloc[0], ordered.iloc[-1]
    return best[label_col], float(best[metric]), worst[label_col], float(worst[metric])
