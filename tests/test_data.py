import io
import math

import numpy as np
import pandas as pd
import pytest

from src.data import REQUIRED_COLUMNS, SchemaError, clean, load_csv, safe_div, validate_schema


def test_validate_schema_accepts_aliases_and_case(raw_df):
    renamed = raw_df.rename(columns={"Channel": "platform", "Spend": " COST ", "Campaign_Goal": "Objective"})
    out = validate_schema(renamed)
    assert list(out.columns) == REQUIRED_COLUMNS


def test_validate_schema_reports_missing_columns(raw_df):
    with pytest.raises(SchemaError, match="Revenue"):
        validate_schema(raw_df.drop(columns=["Revenue"]))


def test_clean_parses_types_and_drops_bad_dates(raw_df):
    raw = raw_df.copy().astype({"Spend": object})
    raw.loc[0, "Spend"] = "$1,234.50"
    raw.loc[1, "Date"] = "not a date"
    raw.loc[2, "Clicks"] = -5
    raw.loc[3, "Channel"] = " ig "
    out = clean(validate_schema(raw))
    assert len(out) == 3
    assert out["Spend"].iloc[0] == pytest.approx(1234.5)
    assert (out["Clicks"] >= 0).all()
    assert set(out["Channel"]) == {"Facebook", "Instagram"}
    assert pd.api.types.is_datetime64_any_dtype(out["Date"])


def test_safe_div_handles_zero():
    out = safe_div([10, 5, 0], [2, 0, 0])
    assert out[0] == 5
    assert np.isnan(out[1]) and np.isnan(out[2])
    assert math.isnan(safe_div(1, 0))
    assert safe_div(6, 3) == 2


def test_derived_metrics(df):
    first = df.iloc[0]
    assert first["CTR"] == pytest.approx(0.02)
    assert first["CPC"] == pytest.approx(0.5)
    assert first["CVR"] == pytest.approx(0.05)
    assert first["CPA"] == pytest.approx(10)
    assert first["ROAS"] == pytest.approx(5)
    assert first["ROI"] == pytest.approx(4)
    zero_conv = df[df["Campaign_ID"] == "C2"].iloc[0]
    assert np.isnan(zero_conv["CPA"])
    assert zero_conv["ROI"] == pytest.approx(-1)


def test_load_csv_round_trip(raw_df):
    buf = io.BytesIO(raw_df.to_csv(index=False).encode())
    out = load_csv(buf)
    assert len(out) == 4 and "ROI" in out.columns


def test_sample_generator_is_seeded_and_valid():
    from scripts.generate_sample_data import generate

    a, b = generate(seed=7), generate(seed=7)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["Channel"]) == {"Facebook", "Instagram", "Pinterest", "Twitter"}
    assert list(validate_schema(a).columns) == REQUIRED_COLUMNS
    assert (a["Conversions"] <= a["Clicks"]).all() and (a["Clicks"] <= a["Impressions"]).all()
