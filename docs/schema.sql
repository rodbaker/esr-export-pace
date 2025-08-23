-- ESR Export Pace Database Schema
-- SQLite implementation

-- Main fact table: world-aggregated weekly export data
CREATE TABLE fact_esr_world_weekly (
    commodity_code INTEGER NOT NULL,
    market_year INTEGER NOT NULL,
    week_ending DATE NOT NULL,
    weekly_exports_mt REAL NOT NULL DEFAULT 0,
    accumulated_exports_mt REAL NOT NULL DEFAULT 0,
    outstanding_sales_mt REAL NOT NULL DEFAULT 0,
    net_sales_mt REAL DEFAULT 0,
    total_commitment_mt REAL NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (commodity_code, market_year, week_ending),
    
    -- Constraints
    CHECK (weekly_exports_mt >= 0),
    CHECK (accumulated_exports_mt >= 0),
    CHECK (outstanding_sales_mt >= 0),
    CHECK (total_commitment_mt >= accumulated_exports_mt),
    CHECK (week_ending = date(week_ending, 'weekday 4'))  -- Thursday validation
);

-- Metadata table for system state and incremental refresh
CREATE TABLE dim_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_esr_commodity_year ON fact_esr_world_weekly(commodity_code, market_year);
CREATE INDEX idx_esr_week_ending ON fact_esr_world_weekly(week_ending);
CREATE INDEX idx_metadata_updated ON dim_metadata(updated_at);

-- Views for common queries
CREATE VIEW v_current_marketing_year AS
SELECT 
    commodity_code,
    market_year,
    week_ending,
    weekly_exports_mt,
    accumulated_exports_mt,
    outstanding_sales_mt,
    total_commitment_mt,
    -- Marketing week index (calculated from June 1 start)
    (julianday(week_ending) - julianday(market_year - 1 || '-06-01')) / 7 + 1 as marketing_week_index
FROM fact_esr_world_weekly
WHERE market_year = (SELECT MAX(market_year) FROM fact_esr_world_weekly)
ORDER BY commodity_code, week_ending;

-- View for pace analysis (requires historical data)
CREATE VIEW v_pace_analysis AS
WITH historical_avg AS (
    SELECT 
        commodity_code,
        (julianday(week_ending) - julianday(market_year - 1 || '-06-01')) / 7 + 1 as marketing_week_index,
        AVG(accumulated_exports_mt) as avg_accumulated_3y,
        AVG(weekly_exports_mt) as avg_weekly_3y,
        AVG(total_commitment_mt) as avg_commitment_3y
    FROM fact_esr_world_weekly
    WHERE market_year >= (SELECT MAX(market_year) - 3 FROM fact_esr_world_weekly)
      AND market_year < (SELECT MAX(market_year) FROM fact_esr_world_weekly)
    GROUP BY commodity_code, marketing_week_index
),
current_year AS (
    SELECT 
        commodity_code,
        (julianday(week_ending) - julianday(market_year - 1 || '-06-01')) / 7 + 1 as marketing_week_index,
        week_ending,
        accumulated_exports_mt,
        weekly_exports_mt,
        total_commitment_mt
    FROM fact_esr_world_weekly
    WHERE market_year = (SELECT MAX(market_year) FROM fact_esr_world_weekly)
)
SELECT 
    c.commodity_code,
    c.marketing_week_index,
    c.week_ending,
    c.accumulated_exports_mt,
    c.weekly_exports_mt,
    c.total_commitment_mt,
    h.avg_accumulated_3y,
    h.avg_weekly_3y,
    h.avg_commitment_3y,
    c.accumulated_exports_mt - h.avg_accumulated_3y as pace_deviation_mt,
    (c.accumulated_exports_mt - h.avg_accumulated_3y) / h.avg_accumulated_3y * 100 as pace_deviation_pct
FROM current_year c
LEFT JOIN historical_avg h ON c.commodity_code = h.commodity_code 
                           AND c.marketing_week_index = h.marketing_week_index
ORDER BY c.commodity_code, c.marketing_week_index;
