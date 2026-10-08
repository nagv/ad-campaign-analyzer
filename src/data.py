"""Loading, validating and enriching campaign CSV data."""
from __future__ import annotations

import re
from pathlib import Path
from typing import IO, Union

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "Date",
    "Campaign_ID",
    "Campaign_Name",
    "Channel",
    "Target_Audience",
    "Campaign_Goal",
    "Spend",
    "Impressions",
    "Clicks",
    "Conversions",
    "Revenue",
]
NUMERIC_COLUMNS = ["Spend", "Impressions", "Clicks", "Conversions", "Revenue"]
CHANNELS = ["Facebook", "Instagram", "Pinterest", "Twitter"]

# Normalised alias -> canonical column name.
_ALIASES = {
    "date": "Date",
    "day": "Date",
    "campaignid": "Campaign_ID",
    "id": "Campaign_ID",
    "campaignname": "Campaign_Name",
    "campaign": "Campaign_Name",
    "name": "Campaign_Name",
    "channel": "Channel",
    "platform": "Channel",
    "channelused": "Channel",
    "targetaudience": "Target_Audience",
    "audience": "Target_Audience",
    "campaigngoal": "Campaign_Goal",
    "goal": "Campaign_Goal",
    "objective": "Campaign_Goal",
    "spend": "Spend",
    "cost": "Spend",
    "acquisitioncost": "Spend",
    "impressions": "Impressions",
    "clicks": "Clicks",
    "conversions": "Conversions",
    "revenue": "Revenue",
}

_CHANNEL_ALIASES = {"fb": "Facebook", "ig": "Instagram", "x": "Twitter", "x (twitter)": "Twitter"}


class SchemaError(ValueError):
    """Raised when the CSV is missing required columns."""


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to canonical names; raise SchemaError if any are missing."""
    rename = {}
    for col in df.columns:
        canonical = _ALIASES.get(_norm(col))
        if canonical and canonical not in rename.values():
            rename[col] = canonical
    out = df.rename(columns=rename)
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise SchemaError(
            "The CSV is missing required column(s): " + ", ".join(missing)
            + ". Expected: " + ", ".join(REQUIRED_COLUMNS) + "."
        )
    return out[REQUIRED_COLUMNS].copy()


def _normalise_channel(value: str) -> str:
    v = str(value).strip()
    return _CHANNEL_ALIASES.get(v.lower(), v.title())


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Parse types, drop unusable rows and clip negative numbers to zero."""
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    for col in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].astype(str).str.replace(r"[$,\s]", "", regex=True)
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).clip(lower=0)
    for col in ["Campaign_ID", "Campaign_Name", "Target_Audience", "Campaign_Goal"]:
        out[col] = out[col].astype(str).str.strip()
    out["Channel"] = out["Channel"].map(_normalise_channel)
    out = out.dropna(subset=["Date"])
    return out.sort_values("Date").reset_index(drop=True)


def safe_div(num, den):
    """Element-wise division returning NaN where the denominator is 0."""
    num = np.asarray(num, dtype="float64")
    den = np.asarray(den, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(den == 0, np.nan, num / np.where(den == 0, 1, den))
    return result if result.ndim else float(result)


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add CTR, CPC, CVR, CPA, ROAS and ROI computed from the row's totals."""
    out = df.copy()
    out["CTR"] = safe_div(out["Clicks"], out["Impressions"])
    out["CPC"] = safe_div(out["Spend"], out["Clicks"])
    out["CVR"] = safe_div(out["Conversions"], out["Clicks"])
    out["CPA"] = safe_div(out["Spend"], out["Conversions"])
    out["ROAS"] = safe_div(out["Revenue"], out["Spend"])
    out["ROI"] = safe_div(out["Revenue"] - out["Spend"], out["Spend"])
    return out


def load_csv(source: Union[str, Path, IO]) -> pd.DataFrame:
    """Read, validate, clean and enrich a campaign CSV."""
    raw = pd.read_csv(source)
    return add_derived_metrics(clean(validate_schema(raw)))
