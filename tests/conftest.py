import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import add_derived_metrics, clean, validate_schema  # noqa: E402


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """Tiny hand-checkable dataset: 2 channels, 3 campaigns, 4 days."""
    rows = [
        # date, id, name, channel, audience, goal, spend, impr, clicks, conv, revenue
        ("2026-01-01", "C1", "FB Alpha", "Facebook", "Men 18-24", "Increase Sales", 100, 10000, 200, 10, 500),
        ("2026-01-02", "C1", "FB Alpha", "Facebook", "Men 18-24", "Increase Sales", 100, 10000, 100, 10, 300),
        ("2026-01-03", "C2", "IG Beta", "Instagram", "Women 25-34", "Brand Awareness", 200, 20000, 400, 0, 0),
        ("2026-01-04", "C3", "IG Gamma", "Instagram", "Men 18-24", "Increase Sales", 50, 5000, 50, 5, 250),
    ]
    cols = ["Date", "Campaign_ID", "Campaign_Name", "Channel", "Target_Audience", "Campaign_Goal",
            "Spend", "Impressions", "Clicks", "Conversions", "Revenue"]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def df(raw_df) -> pd.DataFrame:
    return add_derived_metrics(clean(validate_schema(raw_df)))
