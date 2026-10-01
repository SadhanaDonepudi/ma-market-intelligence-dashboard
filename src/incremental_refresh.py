"""Simulate month-partitioned incremental refresh (Power BI style).

The fact is partitioned by close month (2019-01 .. 2026-12 = 96 partitions).
A simulated source-change log restates a seeded sample of recently-closed
deals; a trailing-3-month refresh policy then re-scans only the partitions
that overlap the policy window, instead of the full 18,000-row fact.

Prints rows scanned vs. rows in a full refresh, using the real partition
sizes from data/transactions.csv. Also writes
outputs/incremental_refresh_summary.csv.

SYNTHETIC DATA - demonstration only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
POLICY_MONTHS = 3  # trailing partitions refreshed (detect-changes window)


def main() -> None:
    deals = pd.read_csv(ROOT / "data" / "transactions.csv", parse_dates=["close_date"])
    total_rows = len(deals)
    deals["partition"] = deals["close_date"].dt.to_period("M").astype(str)

    partitions = (deals.groupby("partition")
                  .size().rename("rows").reset_index().sort_values("partition"))
    # Announcements start 2019-01-01 with a >=30-day close lag, so the first
    # non-empty close partition is 2019-02; expect one partition per month
    # from the first to the last close month, with no gaps.
    expected = pd.period_range(deals["close_date"].min(), deals["close_date"].max(), freq="M")
    assert len(partitions) == len(expected), (
        f"expected {len(expected)} monthly partitions, got {len(partitions)}")

    # Simulated source-change log: restatements land only in the trailing window.
    window_end = deals["close_date"].max()
    window_start = window_end - pd.DateOffset(months=POLICY_MONTHS) + pd.Timedelta(days=1)
    rng = np.random.default_rng(SEED)
    recent = deals[deals["close_date"] >= window_start]
    changed_ids = rng.choice(recent["deal_id"], size=min(250, len(recent)), replace=False)

    refreshed = partitions[partitions["partition"] >= str(window_start.to_period("M"))]
    rows_scanned = int(refreshed["rows"].sum())

    out = ROOT / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame([{
        "total_rows_fact": total_rows,
        "monthly_partitions": len(partitions),
        "policy": f"trailing {POLICY_MONTHS} months",
        "simulated_changed_deals": len(changed_ids),
        "partitions_refreshed": len(refreshed),
        "rows_scanned_incremental": rows_scanned,
        "rows_scanned_full_refresh": total_rows,
        "scan_reduction_pct": round(100 * (1 - rows_scanned / total_rows), 1),
    }])
    summary.to_csv(out / "incremental_refresh_summary.csv", index=False)

    print(f"fact rows (full refresh would scan): {total_rows:,}")
    print(f"monthly partitions: {len(partitions)} "
          f"({partitions['partition'].iloc[0]} .. {partitions['partition'].iloc[-1]})")
    print(f"policy window: {window_start.date()} .. {window_end.date()} "
          f"(trailing {POLICY_MONTHS}-month window spans {len(refreshed)} partitions incl. partials)")
    print(f"simulated source changes (restated deals in window): {len(changed_ids)}")
    print(f"partitions refreshed: {len(refreshed)} of {len(partitions)}")
    print(f"rows scanned (incremental): {rows_scanned:,}")
    print(f"scan reduction vs full refresh: {100 * (1 - rows_scanned / total_rows):.1f}%")
    print(refreshed.to_string(index=False))
    print(f"wrote {out / 'incremental_refresh_summary.csv'}")


if __name__ == "__main__":
    main()
