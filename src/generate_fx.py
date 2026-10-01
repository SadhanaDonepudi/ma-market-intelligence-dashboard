"""Generate daily ECB-style FX rates (synthetic, seeded random walk).

Produces USD-per-EUR (EURUSD) and USD-per-GBP (GBPUSD) for every calendar day
2019-01-01..2026-12-31 — the same cadence a downstream reporting layer would
consume from an ECB reference-rate extract. **Synthetic: no live ECB/EDGAR
API calls are made.**

Output: data/fx_rates.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fx_rates.csv"


def build_fx(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", "2026-12-31", freq="D")
    n = len(dates)

    def walk(start: float, mu: float, vol: float, kappa: float,
             lo: float, hi: float) -> np.ndarray:
        # Mean-reverting (Ornstein-Uhlenbeck in logs) so the synthetic series
        # stays in a realistic trading range instead of wandering off.
        log_x = np.empty(n)
        log_x[0] = np.log(start)
        for t in range(1, n):
            log_x[t] = (log_x[t - 1] + kappa * (np.log(mu) - log_x[t - 1])
                        + rng.normal(0, vol))
        return np.clip(np.exp(log_x), lo, hi)

    eur = walk(1.14, 1.10, 0.0032, 0.012, 0.98, 1.22)
    gbp = walk(1.31, 1.29, 0.0038, 0.012, 1.08, 1.50)
    return pd.DataFrame({
        "rate_date": dates.strftime("%Y-%m-%d"),
        "eurusd_rate": np.round(eur, 6),  # USD per 1 EUR
        "gbpusd_rate": np.round(gbp, 6),  # USD per 1 GBP
        "source_system": "ECB_SIM_EXTRACT_V1",  # locally simulated, no live API
    })


def main() -> None:
    fx = build_fx()
    assert pd.to_datetime(fx["rate_date"]).min() == pd.Timestamp("2019-01-01")
    assert pd.to_datetime(fx["rate_date"]).max() == pd.Timestamp("2026-12-31")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fx.to_csv(OUT, index=False)
    print(f"wrote {OUT} rows={len(fx)} seed={SEED}")
    print(f"EUR/USD {fx['eurusd_rate'].min():.4f}..{fx['eurusd_rate'].max():.4f} "
          f"(last {fx['eurusd_rate'].iloc[-1]:.4f})")
    print(f"GBP/USD {fx['gbpusd_rate'].min():.4f}..{fx['gbpusd_rate'].max():.4f} "
          f"(last {fx['gbpusd_rate'].iloc[-1]:.4f})")


if __name__ == "__main__":
    main()
