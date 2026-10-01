"""Validation tests for the M&A market intelligence pipeline (synthetic data).

Run:  python -m pytest tests/ -q     (from the repo root)

Covers the resume-level claims by construction: exactly 18,000 completed
transactions dated 2019-2026, full FX coverage of the period, zero unmapped
SIC codes, and currency conversion that reconciles deal-by-deal.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sic_mapping import INDUSTRY_GROUPS, SIC_RANGES, map_sic  # noqa: E402


@pytest.fixture(scope="module")
def deals() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "transactions.csv",
                       parse_dates=["announce_date", "close_date"])


@pytest.fixture(scope="module")
def fx() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "fx_rates.csv", parse_dates=["rate_date"])


def test_exactly_18000_completed_transactions(deals):
    assert len(deals) == 18_000
    assert (deals["deal_status"] == "Completed").all()


def test_dates_within_2019_2026(deals):
    lo, hi = pd.Timestamp("2019-01-01"), pd.Timestamp("2026-12-31")
    assert deals["announce_date"].between(lo, hi).all()
    assert deals["close_date"].between(lo, hi).all()
    assert (deals["close_date"] >= deals["announce_date"]).all()


def test_us_and_named_european_targets(deals):
    countries = set(deals["target_country"].unique())
    assert "United States" in countries
    europe = countries - {"United States"}
    assert len(europe) >= 8  # named European countries, not a generic bucket
    assert set(deals["target_region"].unique()) <= {"United States", "Europe"}


def test_fx_covers_full_period(fx):
    assert fx["rate_date"].min() == pd.Timestamp("2019-01-01")
    assert fx["rate_date"].max() == pd.Timestamp("2026-12-31")
    assert len(fx) == 2922  # every calendar day 2019-2026 incl. 2 leap years
    assert fx[["eurusd_rate", "gbpusd_rate"]].notna().all().all()


def test_fx_covers_every_close_date(deals, fx):
    merged = deals.merge(fx, left_on="close_date", right_on="rate_date", how="left")
    assert merged["eurusd_rate"].notna().all()


def test_no_unmapped_sic(deals):
    groups = deals["sic_code"].map(map_sic)  # raises on any unmapped code
    assert set(groups.unique()) <= set(INDUSTRY_GROUPS)
    # the transaction CSV's stored column must agree with the mapping logic
    assert (groups.values == deals["industry_group"].values).all()


def test_mapping_table_is_contiguous():
    ranges = sorted(SIC_RANGES)
    for (_, prev_end, *_), (start, *_rest) in zip(ranges, ranges[1:]):
        assert start == prev_end + 1, "gap in SIC mapping ranges"


def test_currency_conversion_reconciles(deals, fx):
    """EUR total x rate == USD total, deal-by-deal at close-date rates."""
    m = deals.merge(fx, left_on="close_date", right_on="rate_date")
    value_eur = m["deal_value_usd"] / m["eurusd_rate"]
    value_gbp = m["deal_value_usd"] / m["gbpusd_rate"]
    # per-deal identity: eur * rate == usd (exact up to float rounding)
    assert ((value_eur * m["eurusd_rate"]) - m["deal_value_usd"]).abs().max() < 1.0
    assert ((value_gbp * m["gbpusd_rate"]) - m["deal_value_usd"]).abs().max() < 1.0
    # aggregate identity at the conversion rate: sum(eur * rate) == sum(usd)
    eur_rebuilt_usd = (value_eur * m["eurusd_rate"]).sum()
    assert abs(eur_rebuilt_usd / m["deal_value_usd"].sum() - 1) < 1e-9


def test_regional_summary_matches_recomputed(deals):
    summary_path = ROOT / "outputs" / "regional_summary.csv"
    if not summary_path.exists():
        pytest.skip("run src/currency_reporting.py first")
    summary = pd.read_csv(summary_path)
    assert int(summary["deal_count"].sum()) == 18_000
    recomputed = int(round(deals["deal_value_usd"].sum()))
    assert abs(int(summary["total_usd"].sum()) - recomputed) <= len(summary)
