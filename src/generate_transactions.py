"""Generate the synthetic M&A transaction extract.

Simulates a locally-built SEC EDGAR / ECB-style extract: **no live API calls
are made**. Exactly 18,000 completed transactions, 2019-2026, U.S. targets plus
targets in named European countries, each with a 4-digit SIC code mapped to an
IB industry group via :mod:`sic_mapping`.

Output: data/transactions.csv  (deterministic, fixed seed 42)

SYNTHETIC DATA - generated for portfolio/demonstration purposes only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sic_mapping import map_sic  # noqa: E402

SEED = 42
N_DEALS = 18_000
DATE_MIN = pd.Timestamp("2019-01-01")
DATE_MAX = pd.Timestamp("2026-12-31")
# Latest announcement that still leaves room for a 30-270 day close lag.
ANNOUNCE_MAX = pd.Timestamp("2026-04-04")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "transactions.csv"

TARGET_WEIGHTS = {  # share of deals by target country (sums to 1)
    "United States": 0.52,
    "United Kingdom": 0.10,
    "Germany": 0.09,
    "France": 0.08,
    "Netherlands": 0.05,
    "Spain": 0.04,
    "Italy": 0.04,
    "Ireland": 0.03,
    "Switzerland": 0.025,
    "Sweden": 0.025,
}

EUROPEAN_COUNTRIES = [c for c in TARGET_WEIGHTS if c != "United States"]

# (SIC code, relative sampling weight). A realistic M&A code pool; the mapping
# to industry groups is applied through sic_mapping.map_sic, never hardcoded.
SIC_POOL = [
    # Consumer
    (5411, 5), (5812, 4), (2011, 3), (2086, 2), (5999, 4), (7011, 2), (2021, 2),
    # Healthcare (2834 pharma, 2836 biologics, 3841/3845 devices, 8011/8082 care)
    (2834, 6), (2836, 4), (3841, 3), (3845, 3), (8011, 4), (8082, 3),
    # Industrial
    (3711, 4), (3531, 3), (3312, 2), (4911, 3), (4213, 4), (2911, 2), (5084, 3),
    (3599, 3), (3441, 2),
    # Technology & Services
    (7374, 8), (7371, 6), (7372, 5), (6021, 4), (6411, 3), (4813, 3), (4899, 3),
    (8742, 3), (8748, 2), (7363, 2), (6719, 2),
]

TARGET_SUFFIX = ["Holdings", "Group", "Ltd", "Inc", "Corp", "Partners", "Systems",
                 "Labs", "Industries", "Technologies", "Health", "Foods", "Media"]
TARGET_STEM = ["Apex", "Northstar", "Bluehaven", "Cedarpoint", "Quantia", "Velora",
               "Brightpath", "Corebridge", "Medallia", "Foodlink", "Transnova",
               "Alpine", "Summit", "Harborview", "Greenleaf", "Novapay", "Carewell",
               "Logiprime", "Energiq", "Softlayer", "Retailia", "Protea", "Industria"]
ACQUIRER_STEM = ["GlobalCap", "Meridian", "Blackpine", "EuroVest", "Atlantic Partners",
                 "Kingsway", "Nordhaus", "Silverline", "OmniGroup", "Vantia",
                 "Helios Capital", "TransGlobe", "PrimeEquity", "Corelink"]


def build_transactions(seed: int = SEED, n: int = N_DEALS) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    countries = list(TARGET_WEIGHTS)
    weights = np.array([TARGET_WEIGHTS[c] for c in countries], dtype=float)
    target_country = rng.choice(countries, size=n, p=weights / weights.sum())
    acquirer_country = rng.choice(countries, size=n, p=weights / weights.sum())

    sic_codes_pool = np.array([code for code, _ in SIC_POOL])
    sic_weights = np.array([w for _, w in SIC_POOL], dtype=float)
    sic_codes = rng.choice(sic_codes_pool, size=n, p=sic_weights / sic_weights.sum())

    # Announcement dates spread across 2019..Apr 2026; close = announce + lag.
    span_days = (ANNOUNCE_MAX - DATE_MIN).days
    announce = DATE_MIN + pd.to_timedelta(rng.integers(0, span_days + 1, size=n), unit="D")
    lag = rng.integers(30, 271, size=n)
    close = announce + pd.to_timedelta(lag, unit="D")
    assert close.max() <= DATE_MAX, close.max()

    # Deal value: lognormal (USD), median ~ $82M, winsorised at $4.8B for realism.
    deal_value_usd = np.exp(rng.normal(np.log(82e6), 1.05, size=n))
    deal_value_usd = np.clip(deal_value_usd, 1.2e6, 4.8e9).round(0)

    target_name = [f"{rng.choice(TARGET_STEM)} {rng.choice(TARGET_SUFFIX)}" for _ in range(n)]
    acquirer_name = [f"{rng.choice(ACQUIRER_STEM)}" for _ in range(n)]

    df = pd.DataFrame({
        "deal_id": [f"DEAL-{i:05d}" for i in range(1, n + 1)],
        "announce_date": announce.strftime("%Y-%m-%d"),
        "close_date": close.strftime("%Y-%m-%d"),
        "target_name": target_name,
        "acquirer_name": acquirer_name,
        "target_country": target_country,
        "acquirer_country": acquirer_country,
        "sic_code": sic_codes.astype(int),
        "deal_value_usd": deal_value_usd.astype(int),
        "deal_status": "Completed",
        "deal_type": rng.choice(["Acquisition", "Merger", "Buyout", "Carve-out"],
                                size=n, p=[0.58, 0.17, 0.16, 0.09]),
        "payment_type": rng.choice(["Cash", "Stock", "Cash & Stock"], size=n,
                                   p=[0.55, 0.20, 0.25]),
        "source_system": "SEC_EDGAR_SIM_EXTRACT_V1",  # locally simulated, no live API
    })
    df["target_region"] = np.where(df["target_country"] == "United States",
                                   "United States", "Europe")
    df["acquirer_region"] = np.where(df["acquirer_country"] == "United States",
                                     "United States", "Europe")
    df["industry_group"] = df["sic_code"].map(map_sic)
    df["cross_border"] = (df["target_country"] != df["acquirer_country"]).map(
        {True: "Yes", False: "No"})

    cols = ["deal_id", "announce_date", "close_date", "target_name", "acquirer_name",
            "target_country", "target_region", "acquirer_country", "acquirer_region",
            "sic_code", "industry_group", "deal_value_usd", "deal_status",
            "deal_type", "payment_type", "cross_border", "source_system"]
    return df[cols]


def main() -> None:
    df = build_transactions()
    assert len(df) == N_DEALS, f"expected {N_DEALS} rows, got {len(df)}"
    announce = pd.to_datetime(df["announce_date"])
    close = pd.to_datetime(df["close_date"])
    assert announce.between(DATE_MIN, DATE_MAX).all()
    assert close.between(DATE_MIN, DATE_MAX).all()
    assert (close >= announce).all()
    assert (df["deal_status"] == "Completed").all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} rows={len(df)} seed={SEED}")
    print(df["industry_group"].value_counts().to_string())
    print(df["target_region"].value_counts().to_string())
    print(f"close_date range: {close.min().date()} -> {close.max().date()}")


if __name__ == "__main__":
    main()
