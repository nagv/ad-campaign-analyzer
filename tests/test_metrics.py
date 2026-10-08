import math

import pytest

from src import metrics


def test_kpis_recompute_ratios_from_totals(df):
    k = metrics.kpis(df)
    assert k["Spend"] == 450
    assert k["Revenue"] == 1050
    assert k["Conversions"] == 25
    assert k["ROI"] == pytest.approx((1050 - 450) / 450)
    assert k["CPA"] == pytest.approx(450 / 25)
    assert k["CTR"] == pytest.approx(750 / 45000)
    # Averaging row-level ROI would give a different (wrong) answer.
    assert k["ROI"] != pytest.approx(df["ROI"].mean())


def test_by_channel(df):
    t = metrics.by_channel(df).set_index("Channel")
    assert t.loc["Facebook", "Spend"] == 200
    assert t.loc["Facebook", "ROI"] == pytest.approx(3.0)
    assert t.loc["Instagram", "CPA"] == pytest.approx(250 / 5)
    assert t["Spend_Share"].sum() == pytest.approx(1)
    assert list(metrics.by_channel(df)["Channel"]) == ["Instagram", "Facebook"]  # sorted by spend


def test_by_campaign(df):
    t = metrics.by_campaign(df).set_index("Campaign_ID")
    assert len(t) == 3
    assert t.loc["C1", "Clicks"] == 300
    assert t.loc["C1", "Start"].day == 1 and t.loc["C1", "End"].day == 2
    assert math.isnan(t.loc["C2", "CPA"])


@pytest.mark.parametrize("freq,periods", [("Daily", 4), ("Weekly", 1), ("Monthly", 1)])
def test_time_series_granularity(df, freq, periods):
    ts = metrics.time_series(df, freq)
    assert len(ts) == periods
    assert ts["Spend"].sum() == 450


def test_time_series_split_by_channel(df):
    ts = metrics.time_series(df, "Monthly", split_by="Channel")
    assert set(ts["Channel"]) == {"Facebook", "Instagram"}


def test_pct_change():
    assert metrics.pct_change(120, 100) == pytest.approx(0.2)
    assert metrics.pct_change(-50, -100) == pytest.approx(0.5)
    assert metrics.pct_change(5, 0) is None
    assert metrics.pct_change(5, None) is None
    assert metrics.pct_change(float("nan"), 3) is None


def test_best_and_worst_respects_direction(df):
    t = metrics.by_channel(df)
    assert metrics.best_and_worst(t, "ROI")[0] == "Facebook"
    assert metrics.best_and_worst(t, "CPA")[0] == "Facebook"  # lower CPA is better
    assert metrics.best_and_worst(t.assign(ROI=float("nan")), "ROI") is None
