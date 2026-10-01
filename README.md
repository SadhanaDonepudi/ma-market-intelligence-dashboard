# M&A Market Intelligence Dashboard — U.S. & Europe

> ## ⚠️ SYNTHETIC DATA
> Every row in this repository is **synthetically generated** (fixed seed 42)
> for portfolio and demonstration purposes. The pipeline **simulates** an
> SEC EDGAR / ECB-style extract locally — **no live API calls are made** and
> no real transactions, companies, or rates are represented. Company names
> are invented. Deal values follow a calibrated log-normal distribution;
> FX series are seeded, mean-reverting random walks in realistic ranges.

An end-to-end market-intelligence pipeline over **18,000 completed M&A
transactions (2019–2026)** spanning U.S. targets and targets in nine named
European countries: a deterministic transaction generator, a SIC →
investment-banking industry-group mapping implemented in **both SQL
(Snowflake, CTEs) and Python**, a daily FX layer (EUR/USD, GBP/USD) with a
currency-switching reporting layer, a Power BI dataset specification for a
5M+ row fact with incremental refresh, and a simulation of that refresh
policy against the synthetic fact.

## Architecture

```
SEC EDGAR (simulated extract)                ECB-style FX (simulated extract)
        │                                              │
        ▼                                              ▼
src/generate_transactions.py ──► data/transactions.csv (18,000 deals)
                                src/generate_fx.py ──► data/fx_rates.csv (2,922 days)
        │                                              │
        ├── SIC → industry group                       │
        │     src/sic_mapping.py  (Python)             │
        │     sql/sic_mapping.sql (Snowflake DDL + CTE mapping view)
        │     data/sic_industry_groups.csv (reference table)
        │                                              │
        └──────────────► src/currency_reporting.py ◄───┘  (deal-date FX conversion)
                                │
                                ▼
                   outputs/regional_summary.csv / .md
                                │
                   src/incremental_refresh.py ──► outputs/incremental_refresh_summary.csv
                                │
                   docs/powerbi_dataset_spec.md (star schema, 5M+ row design,
                   RangeStart/RangeEnd incremental refresh, currency-switching DAX)
```

## How to run

```bash
pip install -r requirements.txt

python src/generate_transactions.py   # -> data/transactions.csv (18,000 rows, seed 42)
python src/generate_fx.py             # -> data/fx_rates.csv      (2,922 rows, seed 42)
python src/currency_reporting.py      # -> outputs/regional_summary.csv / .md
python src/incremental_refresh.py     # -> outputs/incremental_refresh_summary.csv
python -m pytest tests/ -q            # 9 tests
```

Generators are deterministic: re-running reproduces byte-identical CSVs
(md5-verified).

## Results (actual outputs of the commands above)

**Transactions** — exactly **18,000** completed deals; announcements
2019-01-01 → 2026-04-04, closes 2019-02-01 → 2026-12-22 (mean close lag
150.3 days); median deal value **$80.3M**; 69.7% cross-border; 33 distinct
SIC codes, all mapped (zero unmapped — asserted in tests).

| Target region | Deals | Total USD | Total EUR | Total GBP | Median USD |
|---|---:|---:|---:|---:|---:|
| United States | 9,364 | $1,319,763.7M | €1,210,312.7M | £1,024,380.1M | $79.9M |
| Europe | 8,636 | $1,232,204.1M | €1,130,163.7M | £956,924.5M | $80.6M |
| **Total** | **18,000** | **$2,552.0B** | **€2,340.5B** | **£1,981.3B** | **$80.3M** |

Top European target markets: United Kingdom 1,782 deals ($259.3B), Germany
1,659 ($234.4B), France 1,439 ($210.5B). By industry group: Technology &
Services 6,593 deals ($931.1B), Industrial 4,250 ($593.1B), Healthcare 3,622
($519.5B), Consumer 3,535 ($508.2B). Full country/industry tables:
`outputs/regional_summary.md`.

**FX layer** — 2,922 daily rates, 2019-01-01 → 2026-12-31. EUR/USD range
1.0155–1.1579 (final 1.1089); GBP/USD 1.2123–1.3703 (final 1.2953).
Conversion is at each deal's **close-date rate**
(`value_eur = value_usd / eurusd_rate`), so EUR × rate reconciles to USD
deal-by-deal — enforced by `test_currency_conversion_reconciles` (aggregate
identity holds to <1e-9 relative error).

**Incremental refresh simulation** — fact partitioned into **95 monthly
close partitions** (Feb 2019–Dec 2026). A simulated change log restates 153
deals inside the trailing 3-month policy window (2026-09-23 → 2026-12-22,
spanning 4 partitions incl. partials). Refreshing only those partitions
scans **220 rows vs 18,000 for a full refresh — a 98.8% scan reduction**
(`outputs/incremental_refresh_summary.csv`).

**Tests** — `9 passed`: exact row count, date range, U.S. + named European
targets, FX full-period and per-close-date coverage, zero unmapped SICs,
mapping-range contiguity, deal-by-deal currency reconciliation, and
regional-summary totals matching the raw extract.

## Notes on scope (read before citing)

- The resume this project supports says "18K+ transactions"; the synthetic
  extract is **exactly 18,000 by construction** (asserted), i.e. at the
  18K mark rather than above it.
- The **5M+ row** figure in `docs/powerbi_dataset_spec.md` is the
  *production design target* (deal-line/tranche grain); the shipped
  synthetic fact is the 18,000-row deal-level rollup, and the incremental
  refresh simulation runs against those 18,000 real rows. The spec is
  explicit about this distinction.
- Snowflake DDL is provided as deployable SQL; the local pipeline
  reproduces the same logic in pandas so the whole project runs without a
  warehouse.

## Layout

```
data/     transactions.csv, fx_rates.csv, sic_industry_groups.csv
src/      generate_transactions.py, generate_fx.py, currency_reporting.py,
          incremental_refresh.py, sic_mapping.py
sql/      sic_mapping.sql (Snowflake star schema + CTE mapping view)
docs/     powerbi_dataset_spec.md (5M+ row dataset, refresh policy, DAX)
outputs/  regional_summary.csv/.md, incremental_refresh_summary.csv
tests/    test_project.py (9 tests)
```
