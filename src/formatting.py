"""Display formatting so every metric carries a clear unit."""
from __future__ import annotations

import math

MISSING = "—"

METRIC_LABELS = {
    "Spend": "Spend ($)",
    "Impressions": "Impressions",
    "Clicks": "Clicks",
    "Conversions": "Conversions",
    "Revenue": "Revenue ($)",
    "CTR": "CTR (%)",
    "CPC": "CPC ($)",
    "CVR": "Conversion rate (%)",
    "CPA": "CPA ($)",
    "ROAS": "ROAS (×)",
    "ROI": "ROI (%)",
}

CURRENCY = {"Spend", "Revenue", "CPC", "CPA"}
PERCENT = {"CTR", "CVR", "ROI", "Spend_Share"}
RATIO = {"ROAS"}


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def fmt_currency(value, decimals: int | None = None) -> str:
    if _missing(value):
        return MISSING
    if decimals is None:
        decimals = 2 if abs(value) < 100 else 0
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs(value) >= 10_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.{decimals}f}"


def fmt_pct(value, decimals: int = 1) -> str:
    if _missing(value):
        return MISSING
    return f"{value * 100:,.{decimals}f}%"


def fmt_int(value) -> str:
    if _missing(value):
        return MISSING
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    return f"{value:,.0f}"


def fmt_ratio(value, decimals: int = 2) -> str:
    if _missing(value):
        return MISSING
    return f"{value:,.{decimals}f}×"


def fmt_metric(metric: str, value) -> str:
    if metric in CURRENCY:
        return fmt_currency(value)
    if metric in PERCENT:
        return fmt_pct(value)
    if metric in RATIO:
        return fmt_ratio(value)
    return fmt_int(value)


def label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric)
