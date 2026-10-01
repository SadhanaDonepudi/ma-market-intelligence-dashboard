-- ============================================================================
-- M&A Market Intelligence Dashboard - Snowflake schema + SIC mapping
-- SYNTHETIC DATA: locally simulated SEC EDGAR / ECB-style extracts.
-- No live API calls are made by this project; the tables below describe the
-- warehouse layer the Python pipeline (src/) reproduces locally.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Reference: SIC -> IB industry group (mirrors src/sic_mapping.py and
-- data/sic_industry_groups.csv). Range-based so every 4-digit SIC maps.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE ref_sic_industry_group (
    sic_start       NUMBER(4,0)  NOT NULL,
    sic_end         NUMBER(4,0)  NOT NULL,
    sic_division    VARCHAR(120) NOT NULL,
    industry_group  VARCHAR(40)  NOT NULL
        CONSTRAINT ck_industry_group CHECK (industry_group IN
            ('Consumer','Healthcare','Industrial','Technology & Services'))
);

INSERT INTO ref_sic_industry_group VALUES
 ( 100,  999,'A - Agriculture, Forestry & Fishing','Consumer'),
 (1000, 1499,'B - Mining','Industrial'),
 (1500, 1799,'C - Construction','Industrial'),
 (1800, 1999,'C - Construction, Special Trade Contractors n.e.c.','Industrial'),
 (2000, 2199,'D - Manufacturing (Food & Tobacco)','Consumer'),
 (2200, 2399,'D - Manufacturing (Textiles & Apparel)','Consumer'),
 (2400, 2699,'D - Manufacturing (Lumber, Wood & Paper)','Industrial'),
 (2700, 2799,'D - Manufacturing (Printing & Publishing)','Technology & Services'),
 (2800, 2829,'D - Manufacturing (Basic Chemicals)','Industrial'),
 (2830, 2839,'D - Manufacturing (Pharmaceuticals & Biotech)','Healthcare'),
 (2840, 2849,'D - Manufacturing (Soaps, Cosmetics & Personal Care)','Consumer'),
 (2850, 2899,'D - Manufacturing (Chemicals n.e.c.)','Industrial'),
 (2900, 2999,'D - Manufacturing (Petroleum Refining)','Industrial'),
 (3000, 3399,'D - Manufacturing (Rubber, Stone, Glass & Metals)','Industrial'),
 (3400, 3599,'D - Manufacturing (Fabricated Metal & Machinery)','Industrial'),
 (3600, 3699,'D - Manufacturing (Electronic & Electrical Equipment)','Technology & Services'),
 (3700, 3799,'D - Manufacturing (Transportation Equipment)','Industrial'),
 (3800, 3839,'D - Manufacturing (Instruments & Measuring Devices)','Technology & Services'),
 (3840, 3849,'D - Manufacturing (Medical Instruments & Supplies)','Healthcare'),
 (3850, 3999,'D - Manufacturing (Instruments n.e.c. & Misc.)','Consumer'),
 (4000, 4499,'E - Transportation & Logistics','Industrial'),
 (4500, 4799,'E - Air Transport & Transport Services','Industrial'),
 (4800, 4899,'E - Communications','Technology & Services'),
 (4900, 4999,'E - Electric, Gas & Sanitary Services (Utilities)','Industrial'),
 (5000, 5099,'F - Wholesale Trade, Durable Goods','Industrial'),
 (5100, 5199,'F - Wholesale Trade, Nondurable Goods','Consumer'),
 (5200, 5999,'G - Retail Trade','Consumer'),
 (6000, 6999,'H - Finance, Insurance & Real Estate','Technology & Services'),
 (7000, 7299,'I - Hotels & Personal Services','Consumer'),
 (7300, 7399,'I - Business Services (incl. Software, SIC 737x)','Technology & Services'),
 (7400, 7699,'I - Automotive & Misc. Repair Services','Consumer'),
 (7700, 7999,'I - Leisure & Entertainment Services','Consumer'),
 (8000, 8099,'I - Health Services','Healthcare'),
 (8100, 8299,'I - Legal & Education Services','Technology & Services'),
 (8300, 8399,'I - Social Services','Healthcare'),
 (8400, 8999,'I - Membership, Engineering & Misc. Services','Technology & Services'),
 (9000, 9999,'J - Public Administration & Nonclassifiable','Technology & Services');

-- ---------------------------------------------------------------------------
-- Dimensions & fact (star schema; see docs/powerbi_dataset_spec.md)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_sic_industry (
    sic_code        NUMBER(4,0) PRIMARY KEY,
    sic_division    VARCHAR(120),
    industry_group  VARCHAR(40)
);

CREATE OR REPLACE TABLE dim_geography (
    country         VARCHAR(60) PRIMARY KEY,
    region          VARCHAR(20)   -- 'United States' | 'Europe'
);

CREATE OR REPLACE TABLE dim_currency (
    currency_code   VARCHAR(3) PRIMARY KEY,   -- USD | EUR | GBP
    currency_name   VARCHAR(30),
    symbol          VARCHAR(4)
);

CREATE OR REPLACE TABLE dim_date (
    date_key        DATE PRIMARY KEY,
    year            NUMBER(4,0),
    quarter         NUMBER(1,0),
    month           NUMBER(2,0),
    year_month      VARCHAR(7)
);

CREATE OR REPLACE TABLE fact_ma_transaction (
    deal_id             VARCHAR(20) PRIMARY KEY,
    announce_date       DATE REFERENCES dim_date(date_key),
    close_date          DATE REFERENCES dim_date(date_key),
    target_country      VARCHAR(60) REFERENCES dim_geography(country),
    acquirer_country    VARCHAR(60) REFERENCES dim_geography(country),
    target_region       VARCHAR(20),
    acquirer_region     VARCHAR(20),
    sic_code            NUMBER(4,0) REFERENCES dim_sic_industry(sic_code),
    industry_group      VARCHAR(40),
    deal_value_usd      NUMBER(18,2),
    deal_status         VARCHAR(20),
    deal_type           VARCHAR(30),
    payment_type        VARCHAR(30),
    cross_border        VARCHAR(3),
    source_system       VARCHAR(40)
)
CLUSTER BY (close_date);  -- monthly close-date clustering = refresh partitions

CREATE OR REPLACE TABLE fact_fx_rate (
    rate_date       DATE PRIMARY KEY,
    eurusd_rate     NUMBER(12,6),   -- USD per 1 EUR
    gbpusd_rate     NUMBER(12,6),   -- USD per 1 GBP
    source_system   VARCHAR(40)
);

-- ---------------------------------------------------------------------------
-- Mapping view, expressed with CTEs: every transaction SIC resolves to
-- exactly one division + industry group; unmatched codes surface as
-- 'UNMAPPED' so a data-quality check can assert the count is zero.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_transaction_industry AS
WITH sic_lookup AS (
    SELECT sic_start, sic_end, sic_division, industry_group
    FROM ref_sic_industry_group
),
mapped AS (
    SELECT
        t.deal_id,
        t.sic_code,
        COALESCE(l.sic_division, 'UNMAPPED')    AS sic_division,
        COALESCE(l.industry_group, 'UNMAPPED')  AS industry_group_mapped
    FROM fact_ma_transaction t
    LEFT JOIN sic_lookup l
      ON t.sic_code BETWEEN l.sic_start AND l.sic_end
)
SELECT * FROM mapped;

-- Data-quality check (must return 0):
-- SELECT COUNT(*) FROM vw_transaction_industry WHERE industry_group_mapped = 'UNMAPPED';
