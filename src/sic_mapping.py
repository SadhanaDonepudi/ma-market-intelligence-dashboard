"""SIC -> IB industry-group mapping (Python implementation).

The same mapping is expressed in SQL in ``sql/sic_mapping.sql`` and as a
reference table in ``data/sic_industry_groups.csv``. The ranges below follow
the standard U.S. SIC division structure and consolidate every division into
one of the four investment-banking industry groups used on the dashboard:

    Consumer, Healthcare, Industrial, Technology & Services

Ranges are contiguous over 0100-9999 so that any well-formed 4-digit SIC
code maps to exactly one industry group (the test suite asserts zero
unmapped codes across the synthetic transaction extract).
"""

from __future__ import annotations

# (sic_start, sic_end, sic_division, industry_group)
SIC_RANGES: list[tuple[int, int, str, str]] = [
    (100, 999, "A - Agriculture, Forestry & Fishing", "Consumer"),
    (1000, 1499, "B - Mining", "Industrial"),
    (1500, 1799, "C - Construction", "Industrial"),
    (1800, 1999, "C - Construction, Special Trade Contractors n.e.c.", "Industrial"),
    (2000, 2199, "D - Manufacturing (Food & Tobacco)", "Consumer"),
    (2200, 2399, "D - Manufacturing (Textiles & Apparel)", "Consumer"),
    (2400, 2699, "D - Manufacturing (Lumber, Wood & Paper)", "Industrial"),
    (2700, 2799, "D - Manufacturing (Printing & Publishing)", "Technology & Services"),
    (2800, 2829, "D - Manufacturing (Basic Chemicals)", "Industrial"),
    (2830, 2839, "D - Manufacturing (Pharmaceuticals & Biotech)", "Healthcare"),
    (2840, 2849, "D - Manufacturing (Soaps, Cosmetics & Personal Care)", "Consumer"),
    (2850, 2899, "D - Manufacturing (Chemicals n.e.c.)", "Industrial"),
    (2900, 2999, "D - Manufacturing (Petroleum Refining)", "Industrial"),
    (3000, 3399, "D - Manufacturing (Rubber, Stone, Glass & Metals)", "Industrial"),
    (3400, 3599, "D - Manufacturing (Fabricated Metal & Machinery)", "Industrial"),
    (3600, 3699, "D - Manufacturing (Electronic & Electrical Equipment)", "Technology & Services"),
    (3700, 3799, "D - Manufacturing (Transportation Equipment)", "Industrial"),
    (3800, 3839, "D - Manufacturing (Instruments & Measuring Devices)", "Technology & Services"),
    (3840, 3849, "D - Manufacturing (Medical Instruments & Supplies)", "Healthcare"),
    (3850, 3999, "D - Manufacturing (Instruments n.e.c. & Misc.)", "Consumer"),
    (4000, 4499, "E - Transportation & Logistics", "Industrial"),
    (4500, 4799, "E - Air Transport & Transport Services", "Industrial"),
    (4800, 4899, "E - Communications", "Technology & Services"),
    (4900, 4999, "E - Electric, Gas & Sanitary Services (Utilities)", "Industrial"),
    (5000, 5099, "F - Wholesale Trade, Durable Goods", "Industrial"),
    (5100, 5199, "F - Wholesale Trade, Nondurable Goods", "Consumer"),
    (5200, 5999, "G - Retail Trade", "Consumer"),
    (6000, 6999, "H - Finance, Insurance & Real Estate", "Technology & Services"),
    (7000, 7299, "I - Hotels & Personal Services", "Consumer"),
    (7300, 7399, "I - Business Services (incl. Software, SIC 737x)", "Technology & Services"),
    (7400, 7699, "I - Automotive & Misc. Repair Services", "Consumer"),
    (7700, 7999, "I - Leisure & Entertainment Services", "Consumer"),
    (8000, 8099, "I - Health Services", "Healthcare"),
    (8100, 8299, "I - Legal & Education Services", "Technology & Services"),
    (8300, 8399, "I - Social Services", "Healthcare"),
    (8400, 8999, "I - Membership, Engineering & Misc. Services", "Technology & Services"),
    (9000, 9999, "J - Public Administration & Nonclassifiable", "Technology & Services"),
]

INDUSTRY_GROUPS = ("Consumer", "Healthcare", "Industrial", "Technology & Services")


def map_sic(sic_code: int) -> str:
    """Return the IB industry group for a 4-digit SIC code."""
    for start, end, _division, group in SIC_RANGES:
        if start <= int(sic_code) <= end:
            return group
    raise ValueError(f"Unmapped SIC code: {sic_code}")


def sic_division(sic_code: int) -> str:
    """Return the SIC division label for a 4-digit SIC code."""
    for start, end, division, _group in SIC_RANGES:
        if start <= int(sic_code) <= end:
            return division
    raise ValueError(f"Unmapped SIC code: {sic_code}")
