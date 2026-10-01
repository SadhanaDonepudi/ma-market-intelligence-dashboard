# Power BI Dataset Specification — M&A Market Intelligence Dashboard

> **SYNTHETIC DATA.** The extract in this repo (18,000 deals, 2019–2026) is
> locally simulated — no live SEC EDGAR / ECB API calls. The dataset design
> below is written for the production shape of the same model: a **5M+ row
> fact** (deal line items / tranches and daily valuation marks expand one row
> per deal to the multi-million-row grain), so partitioning, incremental
> refresh, and the currency-switching measures are specified at that scale.
> `src/incremental_refresh.py` simulates the same policy against the 18,000
> synthetic rows.

## 1. Star schema

### Fact: `FactDeal` (production grain)
- **Grain:** one row per *deal line item per close-date mark* — the level at
  which consideration tranches (cash / stock / earn-out) and post-close marks
  are recorded. 18K deals × tranches × marks is what carries the production
  fact past 5M rows; the synthetic extract ships the deal-level rollup
  (one row per completed deal) so every measure below aggregates identically.
- **Measures columns:** `DealValueUSD` (stored once, in USD — the single
  source of truth; EUR/GBP are always derived, never stored), tranche value,
  advisory fees.
- **Keys:** `DealKey` (degenerate `DEAL-00001` retained on the fact),
  `CloseDateKey`, `AnnounceDateKey`, `TargetGeographyKey`,
  `AcquirerGeographyKey`, `SICIndustryKey`, `DealTypeKey`.

### Dimensions
| Dimension | Contents | Notes |
|---|---|---|
| `DimDate` | Date, Year, Quarter, Month, YearMonth | Marked as date table; both role-playing relationships (Announce / Close) via `USERELATIONSHIP` |
| `DimGeography` | Country → Region (`United States` / `Europe`) | Snowflake-flattened: one row per country, region as attribute — avoids a snowflaked region table |
| `DimSICIndustry` | SIC code → SIC division → IB industry group | Built from `sql/sic_mapping.sql` / `src/sic_mapping.py`; groups: Consumer, Healthcare, Industrial, Technology & Services |
| `DimCurrency` | USD, EUR, GBP | **Disconnected** (no relationship to the fact) — drives the currency switch |
| `DimDealType` | Acquisition / Merger / Buyout / Carve-out; Payment type | Junk-dimension candidate at scale |

### Design rules
- Store values **only in USD**; convert at query time. Storing three
  currencies triples fact width and invites reconciliation drift.
- Integer surrogate keys on dimensions; the fact stays narrow (keys + 3–4
  numeric columns), which is what keeps a 5M+ row Import model fast under
  VertiPaq compression. Sort the fact load by `CloseDateKey` so date runs
  compress.
- `DimSICIndustry` is Type-1: an SIC re-mapping restates history (IB group
  definitions are presentational, not point-in-time facts).

## 2. Partitioning & incremental refresh

- **Partition column:** `CloseDate` (monthly partitions across the extract
  period — 95 non-empty close partitions, Feb 2019 … Dec 2026, in the
  synthetic extract; Jan 2019 is empty by construction since announcements
  start 2019-01-01 with a ≥30-day close lag. The production fact partitions
  the same way over its full history).
- **Parameters:** `RangeStart` / `RangeEnd` (Date/Time, private) bound the
  fact query: `WHERE CloseDate >= RangeStart AND CloseDate < RangeEnd`.
- **Policy:**
  - Archive: 8 years (full history retained).
  - Incremental refresh: **trailing 3 months** — only partitions overlapping
    the last 3 close-months are re-queried; "Detect data changes" on, using a
    `LastModifiedUTC` watermark column so unchanged partitions in the window
    are skipped.
  - First refresh loads the full archive; subsequent refreshes touch only
    the trailing partitions (+ the current partial month, always refreshed).
- **Why:** restatements in M&A data (revised consideration, late filings)
  overwhelmingly land in the most recent quarters. The simulation in
  `src/incremental_refresh.py` applies a seeded change log of restated deals
  inside the trailing window and scans only those partitions — run it to see
  the real rows-scanned figures for the synthetic fact.

## 3. Currency-switching DAX measures

A disconnected `DimCurrency` slicer (USD / EUR / GBP) switches every value
measure. FX is applied at the deal's **close-date rate** — the same
convention as `src/currency_reporting.py` — so Power BI and the Python
reporting layer reconcile.

```dax
-- Selected reporting currency (from the disconnected slicer)
Selected Currency :=
SELECTEDVALUE ( DimCurrency[CurrencyCode], "USD" )

-- USD stored on the fact, converted per-row at the close-date rate.
-- FactDeal[EURUSD_RateOnClose] / [GBPUSD_RateOnClose] are resolved at load
-- (joined from the FX table on CloseDate), keeping the measure a simple SUMX.
Total Deal Value (Reporting) :=
VAR Cur = [Selected Currency]
RETURN
    SUMX (
        FactDeal,
        DIVIDE (
            FactDeal[DealValueUSD],
            SWITCH (
                Cur,
                "USD", 1,
                "EUR", FactDeal[EURUSD_RateOnClose],
                "GBP", FactDeal[GBPUSD_RateOnClose]
            )
        )
    )

Deal Count :=
DISTINCTCOUNT ( FactDeal[DealKey] )

Avg Deal Value (Reporting) :=
DIVIDE ( [Total Deal Value (Reporting)], [Deal Count] )

Median Deal Value (Reporting) :=
-- median must also switch currency: recompute the converted value per deal
VAR Cur = [Selected Currency]
RETURN
    MEDIANX (
        FactDeal,
        DIVIDE (
            FactDeal[DealValueUSD],
            SWITCH (
                Cur,
                "USD", 1,
                "EUR", FactDeal[EURUSD_RateOnClose],
                "GBP", FactDeal[GBPUSD_RateOnClose]
            )
        )
    )

Total Deal Value (Reporting) YoY % :=
VAR CurVal = [Total Deal Value (Reporting)]
VAR Prior =
    CALCULATE ( [Total Deal Value (Reporting)], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
RETURN
    DIVIDE ( CurVal - Prior, Prior )
```

**Reading the measures.** `Total Deal Value (Reporting)` iterates the fact
once (`SUMX`) so each deal converts at *its own* close-date rate — dividing
an aggregated USD total by a single period rate would not reconcile with
the deal-level reporting layer (the test suite checks the deal-level
identity `EUR × rate = USD`). `Median Deal Value` repeats the pattern with
`MEDIANX` because a median cannot be derived from converted totals. Format
strings switch with the slicer via a calculation group or
`SELECTEDVALUE`-driven format measure (`"$"#,0,,.0"B"` / `"€"#,0,,.0"B"` /
`"£"#,0,,.0"B"`), so one visual serves all three currencies.

## 4. Warehouse counterpart

`sql/sic_mapping.sql` holds the Snowflake DDL for the same star
(`fact_ma_transaction`, `fact_fx_rate`, dimensions), the SIC→industry-group
reference table, and `vw_transaction_industry`, which resolves every SIC
through the range table with CTEs and flags anything unmapped for the
zero-unmapped data-quality check the tests enforce locally.
