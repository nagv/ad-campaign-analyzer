import pytest

from src.formatting import MISSING, fmt_currency, fmt_int, fmt_metric, fmt_pct, fmt_ratio, label


@pytest.mark.parametrize("value,expected", [
    (12.5, "$12.50"), (1234.4, "$1,234"), (439_912, "$439.9K"),(2_500_000, "$2.50M"), (None, MISSING), (float("nan"), MISSING),
])
def test_fmt_currency(value, expected):
    assert fmt_currency(value) == expected


def test_other_formats():
    assert fmt_pct(0.1234) == "12.3%"
    assert fmt_pct(-0.5) == "-50.0%"
    assert fmt_int(12345.6) == "12,346"
    assert fmt_int(3_400_000) == "3.40M"
    assert fmt_ratio(2.345) == "2.35×"
    assert fmt_pct(float("nan")) == fmt_int(None) == fmt_ratio(None) == MISSING


def test_fmt_metric_picks_unit():
    assert fmt_metric("Spend", 50) == "$50.00"
    assert fmt_metric("ROI", 1.5) == "150.0%"
    assert fmt_metric("ROAS", 2.5) == "2.50×"
    assert fmt_metric("Clicks", 1000) == "1,000"
    assert label("CPA") == "CPA ($)" and label("Unknown") == "Unknown"
