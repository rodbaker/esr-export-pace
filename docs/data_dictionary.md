# ESR Export Pace - Data Dictionary

## Overview
This document defines all data fields, transformations, and business rules used in the ESR Export Pace tracking system.

## Core ESR Definitions
*Source: USDA Foreign Agricultural Service Export Sales Reporting Program*

| Term | Definition | Notes |
|------|------------|-------|
| **Weekly Exports** | Shipments of reportable commodities exported against sales for a reporting week Friday through Thursday | Actual physical shipments |
| **Accumulated Exports** | Accumulated shipments of reportable commodities from the beginning of the marketing year to the current week ending date | Season-to-date shipments; revised periodically |
| **Outstanding Sales** | Total outstanding export sales contracts by country/commodity that have not been shipped at any given time during the marketing year | Forward commitments not yet shipped |
| **Gross New Sales** | Includes increases from new export sales, contract adjustments, loading tolerances, changes in marketing year, change in commodity or sales made against exports for the exporter's own account | Includes carryover sales from prior MY |
| **Net Sales** | Sum total resulting from new export sales, increases/decreases from destination changes, decreases from foreign seller purchases, and cancellations | Can be negative due to cancellations |
| **Total Commitment** | Grand total of outstanding sales plus accumulated exports by country/commodity at any given time during the marketing year | Outstanding + Accumulated |

## Database Schema

### fact_esr_world_weekly
Primary fact table storing world-aggregated weekly export data.

| Column | Type | Description | Source | Validation Rules |
|--------|------|-------------|--------|------------------|
| `commodity_code` | INTEGER | USDA commodity identifier (e.g., 107 = All Wheat) | API /commodities | Must exist in commodities config |
| `market_year` | INTEGER | Marketing year (e.g., 2024 for 2023-2024 MY) | API /datareleasedates | Must match API marketYear |
| `week_ending` | DATE | Thursday date ending the ESR reporting week | API weekEndingDate | Must be Thursday; within MY bounds |
| `weekly_exports_mt` | FLOAT | Physical shipments for the week (Metric Tons) | Sum of API weeklyExports across countries | ≥ 0 |
| `accumulated_exports_mt` | FLOAT | Season-to-date shipments (Metric Tons) | Sum of API accumulatedExports across countries | ≥ 0; monotonic within MY |
| `outstanding_sales_mt` | FLOAT | Unshipped contracts (Metric Tons) | Sum of API outstandingSales across countries | ≥ 0 |
| `net_sales_mt` | FLOAT | Net sales activity for the week (Metric Tons) | Sum of API currentMYNetSales across countries | Can be negative |
| `total_commitment_mt` | FLOAT | Total commitments (Metric Tons) | accumulated_exports_mt + outstanding_sales_mt | Must equal sum; ≥ accumulated |
| `updated_at` | TIMESTAMP | When this record was last updated | System generated | ISO 8601 format |

**Primary Key**: `(commodity_code, market_year, week_ending)`

### dim_metadata
Key-value store for system metadata and incremental refresh tracking.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `key` | TEXT | Metadata key identifier | `last_release_timestamp_107` |
| `value` | TEXT | Metadata value (JSON if complex) | `2025-08-14T00:00:00` |
| `updated_at` | TIMESTAMP | When this metadata was set | `2025-08-20T10:30:00Z` |

**Primary Key**: `key`

## Derived Fields & Calculations

### Marketing Week Index
**Formula**: `1 + floor((week_ending - market_year_start) / 7 days)`

- **Purpose**: Align weeks across different marketing years for pace comparison
- **Range**: 1-53 (depending on MY length)
- **Example**: Week ending 2024-06-06 (first Thursday after June 1 start) = Index 1

### Pace Metrics (Future Implementation)
| Metric | Calculation | Purpose |
|--------|-------------|---------|
| `accumulated_vs_avg_3y` | current_accumulated - avg_accumulated_last_3_my | Pace deviation from 3-year average |
| `weekly_vs_avg_3y` | current_weekly - avg_weekly_last_3_my | Weekly shipment comparison |
| `commitment_vs_avg_3y` | current_commitment - avg_commitment_last_3_my | Forward sales comparison |

## Units & Conversions

### Standard Units
- **Primary**: Metric Tons (MT) for all wheat commodities (unitId = 1)
- **Validation**: All data must be in MT; reject records with different unitId
- **Precision**: Store as FLOAT with 2 decimal places for display

### Marketing Year Boundaries
| Commodity | Marketing Year Period | Source |
|-----------|----------------------|--------|
| All Wheat (107) | June 1 - May 31 | API /datareleasedates |
| Wheat Classes (101-106) | June 1 - May 31 | API /datareleasedates |

*Note: Always use API-provided boundaries as truth; config overrides only as fallback*

## Data Quality Rules

### Structural Integrity
1. No duplicate primary keys allowed
2. All `week_ending` dates must be Thursdays
3. All dates must fall within marketing year boundaries
4. All `commodity_code` values must exist in active configuration

### Arithmetic Validation
1. `total_commitment_mt = accumulated_exports_mt + outstanding_sales_mt` (±0.01 tolerance)
2. `accumulated_exports_mt` must be monotonic (non-decreasing) within marketing year
3. All metric ton fields must be non-negative except `net_sales_mt`

### Temporal Validation
1. `week_ending` dates must be sequential (7-day gaps)
2. No future dates beyond current date + 7 days
3. No dates before earliest available ESR data (approximately 1990)

## Change Management

### Revisions
- ESR data is subject to revision; we store latest values only (MVP)
- Use `updated_at` timestamp to track when changes occurred
- Future: implement revision history table if needed

### Schema Evolution
- New columns: Add with DEFAULT values for backward compatibility
- Breaking changes: Require migration scripts in `/migrations/`
- Version schema in `dim_metadata` table: `schema_version`