# Regional M&A Summary (Synthetic Data)

> **SYNTHETIC DATA** — locally simulated SEC EDGAR / ECB-style extracts; no live API calls. Deal-date FX conversion (value_ccy = USD / rate on close date).

## By target region

| Target region | Deals | Total USD | Total EUR | Total GBP | Median USD | Median EUR | Median GBP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Europe | 8,636 | $1,232,204.1M | €1,130,163.7M | £956,924.5M | $80.6M | €74.05M | £62.68M |
| United States | 9,364 | $1,319,763.7M | €1,210,312.7M | £1,024,380.1M | $79.9M | €73.31M | £61.96M |

## By target country

| Target country | Deals | Total USD | Median USD |
|---|---:|---:|---:|
| United States | 9,364 | $1,319,763.7M | $79.9M |
| United Kingdom | 1,782 | $259,295.6M | $78.2M |
| Germany | 1,659 | $234,406.3M | $84.4M |
| France | 1,439 | $210,501.1M | $77.8M |
| Netherlands | 894 | $126,490.9M | $80.7M |
| Italy | 703 | $100,318.5M | $82.6M |
| Spain | 714 | $95,553.2M | $77.7M |
| Ireland | 542 | $83,343.8M | $83.3M |
| Switzerland | 447 | $62,593.6M | $82.7M |
| Sweden | 456 | $59,701.0M | $81.7M |

## By industry group

| Industry group | Deals | Total USD | Median USD |
|---|---:|---:|---:|
| Technology & Services | 6,593 | $931,139.7M | $80.5M |
| Industrial | 4,250 | $593,101.0M | $79.2M |
| Healthcare | 3,622 | $519,492.6M | $81.0M |
| Consumer | 3,535 | $508,234.5M | $80.3M |

_Totals in EUR/GBP depend on each deal's close-date rate; EUR total x rate reconciles to USD only deal-by-deal (rate varies by close date) — see tests._
