"""Currency-switching reporting layer.

Converts every deal's USD value into EUR and GBP at the FX rate in force on
the deal's **close date** (deal-date conversion, the convention a Power BI
currency-switching measure reproduces - see docs/powerbi_dataset_spec.md):

    value_eur = value_usd / eurusd_rate_on_close_date
    value_gbp = value_usd / gbpusd_rate_on_close_date

Writes:
    outputs/regional_summary.csv   region-level summary (one row per region)
    outputs/regional_summary.md    region + country + industry detail

SYNTHETIC DATA - demonstration only.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_and_convert() -> pd.DataFrame:
    deals = pd.read_csv(ROOT / "data" / "transactions.csv", parse_dates=["close_date"])
    fx = pd.read_csv(ROOT / "data" / "fx_rates.csv", parse_dates=["rate_date"])
    merged = deals.merge(fx, left_on="close_date", right_on="rate_date", how="left")
    assert merged["eurusd_rate"].notna().all(), "FX missing for a close date"
    assert merged["gbpusd_rate"].notna().all(), "FX missing for a close date"
    merged["deal_value_eur"] = merged["deal_value_usd"] / merged["eurusd_rate"]
    merged["deal_value_gbp"] = merged["deal_value_usd"] / merged["gbpusd_rate"]
    return merged


def summarise(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    g = df.groupby(group_col).agg(
        deal_count=("deal_id", "count"),
        total_usd=("deal_value_usd", "sum"),
        total_eur=("deal_value_eur", "sum"),
        total_gbp=("deal_value_gbp", "sum"),
        median_usd=("deal_value_usd", "median"),
        median_eur=("deal_value_eur", "median"),
        median_gbp=("deal_value_gbp", "median"),
    ).reset_index()
    for c in [c for c in g.columns if c not in (group_col, "deal_count")]:
        g[c] = g[c].round(0).astype("int64")
    return g


def _fmt_musd(v: float) -> str:
    return f"${v / 1e6:,.1f}M"


def write_markdown(region: pd.DataFrame, country: pd.DataFrame,
                   industry: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Regional M&A Summary (Synthetic Data)\n",
        "> **SYNTHETIC DATA** — locally simulated SEC EDGAR / ECB-style extracts; "
        "no live API calls. Deal-date FX conversion (value_ccy = USD / rate on close date).\n",
        "## By target region\n",
        "| Target region | Deals | Total USD | Total EUR | Total GBP | Median USD | Median EUR | Median GBP |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in region.iterrows():
        lines.append(
            f"| {r['target_region']} | {r['deal_count']:,} | {_fmt_musd(r['total_usd'])} "
            f"| €{r['total_eur'] / 1e6:,.1f}M | £{r['total_gbp'] / 1e6:,.1f}M "
            f"| {_fmt_musd(r['median_usd'])} | €{r['median_eur'] / 1e6:,.2f}M "
            f"| £{r['median_gbp'] / 1e6:,.2f}M |")
    lines += ["", "## By target country\n",
              "| Target country | Deals | Total USD | Median USD |",
              "|---|---:|---:|---:|"]
    for _, r in country.iterrows():
        lines.append(f"| {r['target_country']} | {r['deal_count']:,} | "
                     f"{_fmt_musd(r['total_usd'])} | {_fmt_musd(r['median_usd'])} |")
    lines += ["", "## By industry group\n",
              "| Industry group | Deals | Total USD | Median USD |",
              "|---|---:|---:|---:|"]
    for _, r in industry.iterrows():
        lines.append(f"| {r['industry_group']} | {r['deal_count']:,} | "
                     f"{_fmt_musd(r['total_usd'])} | {_fmt_musd(r['median_usd'])} |")
    lines += ["", "_Totals in EUR/GBP depend on each deal's close-date rate; "
                  "EUR total x rate reconciles to USD only deal-by-deal "
                  "(rate varies by close date) — see tests._\n"]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_and_convert()
    out = ROOT / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    region = summarise(df, "target_region")
    region.to_csv(out / "regional_summary.csv", index=False)

    country = summarise(df, "target_country").sort_values("total_usd", ascending=False)
    industry = summarise(df, "industry_group").sort_values("total_usd", ascending=False)
    write_markdown(region, country, industry, out / "regional_summary.md")

    total_usd = int(df["deal_value_usd"].sum())
    print(region.to_string(index=False))
    print(f"\nTOTAL deals={len(df):,} total_usd=${total_usd/1e9:.2f}B "
          f"total_eur=€{df['deal_value_eur'].sum()/1e9:.2f}B "
          f"total_gbp=£{df['deal_value_gbp'].sum()/1e9:.2f}B")
    print(f"wrote {out / 'regional_summary.csv'}")
    print(f"wrote {out / 'regional_summary.md'}")


if __name__ == "__main__":
    main()
