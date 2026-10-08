"""Generate a seeded, realistic-looking campaign CSV for the dashboard.

Usage: python scripts/generate_sample_data.py [--out data/sample_campaigns.csv] [--seed 42]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

START, END = "2026-04-01", "2026-09-30"

# Per-channel economics: CPM ($), CTR, CVR, average order value ($).
PROFILES = {
    "Facebook":  {"cpm": 9.0,  "ctr": 0.012, "cvr": 0.045, "aov": 62.0},
    "Instagram": {"cpm": 11.0, "ctr": 0.010, "cvr": 0.050, "aov": 68.0},
    "Pinterest": {"cpm": 6.0,  "ctr": 0.008, "cvr": 0.040, "aov": 85.0},
    "Twitter":   {"cpm": 7.5,  "ctr": 0.009, "cvr": 0.022, "aov": 55.0},
}
AUDIENCES = ["Men 18-24", "Women 25-34", "Men 25-34", "Women 35-44", "All Ages"]
GOALS = ["Brand Awareness", "Product Launch", "Increase Sales", "Market Expansion"]
THEMES = ["Summer Sale", "Back to School", "New Arrivals", "Loyalty Push", "Flash Deal", "Holiday Preview"]
# Goal multipliers on CVR: awareness campaigns convert less.
GOAL_CVR = {"Brand Awareness": 0.6, "Product Launch": 1.0, "Increase Sales": 1.3, "Market Expansion": 0.85}


def generate(seed: int = 42, campaigns_per_channel: int = 6) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    all_days = pd.date_range(START, END, freq="D")
    rows = []
    cid = 1000
    for channel, p in PROFILES.items():
        for i in range(campaigns_per_channel):
            cid += 1
            goal = GOALS[rng.integers(len(GOALS))]
            audience = AUDIENCES[rng.integers(len(AUDIENCES))]
            theme = THEMES[i % len(THEMES)]
            length = int(rng.integers(45, 121))
            start_idx = int(rng.integers(0, len(all_days) - length))
            days = all_days[start_idx:start_idx + length]
            base_spend = rng.uniform(80, 400)
            quality = rng.normal(1.0, 0.15)  # campaign-level creative quality
            for d in days:
                weekday = 1.15 if d.dayofweek >= 5 else 1.0
                spend = max(0.0, base_spend * weekday * rng.normal(1, 0.18))
                impressions = int(spend / p["cpm"] * 1000 * rng.normal(1, 0.08))
                ctr = max(0.001, p["ctr"] * quality * rng.normal(1, 0.12))
                clicks = int(rng.binomial(max(impressions, 0), min(ctr, 1)))
                cvr = max(0.0, p["cvr"] * GOAL_CVR[goal] * quality * rng.normal(1, 0.2))
                conversions = int(rng.binomial(clicks, min(cvr, 1))) if clicks else 0
                revenue = round(conversions * p["aov"] * rng.normal(1, 0.1), 2) if conversions else 0.0
                rows.append({
                    "Date": d.date().isoformat(),
                    "Campaign_ID": f"C{cid}",
                    "Campaign_Name": f"{channel} {theme} {i + 1}",
                    "Channel": channel,
                    "Target_Audience": audience,
                    "Campaign_Goal": goal,
                    "Spend": round(spend, 2),
                    "Impressions": max(impressions, 0),
                    "Clicks": clicks,
                    "Conversions": conversions,
                    "Revenue": max(revenue, 0.0),
                })
    return pd.DataFrame(rows).sort_values(["Date", "Campaign_ID"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "sample_campaigns.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    df = generate(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} rows, {df['Campaign_ID'].nunique()} campaigns -> {out}")


if __name__ == "__main__":
    main()
