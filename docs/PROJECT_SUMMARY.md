# ESR Export Pace Analysis - Project Summary

## Overview
Complete USDA ESR (Export Sales Reporting) data pipeline with advanced pace analysis capabilities for tracking US agricultural export performance against historical baselines.

## System Architecture

### Core Components
1. **API Client** (`src/esr_pace/api_client.py`)
   - USDA ESR API integration with query parameter authentication
   - Exponential backoff retry logic for reliability
   - Support for all ESR endpoints

2. **Data Store** (`src/esr_pace/data_store.py`) 
   - SQLite database with comprehensive schema
   - Data cleaning and type conversion for database compatibility
   - World aggregation from country-level data

3. **ETL Pipeline** (`src/esr_pace/etl.py`)
   - Multi-marketing year data processing
   - Data validation integration
   - Force refresh and incremental update support

4. **Validation Framework** (`src/esr_pace/validation.py`)
   - 14+ validation checks across structural, arithmetic, and business logic
   - Severity classification and detailed reporting

5. **Pace Analysis Engine** (`src/esr_pace/pace_calc.py`)
   - 5-year historical baseline calculations (upgraded from 3-year in 2024)
   - Statistical deviation analysis with confidence intervals
   - Interactive Plotly dashboards with Bendigo color theme
   - Comprehensive reporting with insights and recommendations

## Key Features

### Data Processing
- **Marketing Year Support**: June 1 - May 31 agricultural cycles
- **World Aggregation**: Country-level data rolled up to world totals
- **Historical Analysis**: 5-year baseline data (2020-2024) for trend analysis
- **Data Quality**: Comprehensive validation and cleaning pipeline

### Pace Analysis
- **Deviation Tracking**: Week-by-week comparison vs historical averages
- **Statistical Analysis**: Z-scores, confidence intervals, outlier detection
- **Trend Classification**: Ahead/behind/on-pace categorization with severity levels
- **Volatility Scoring**: Quantitative measure of export consistency

### Reporting & Visualization
- **Interactive Charts**: Plotly-based pace analysis and dashboard views
- **Executive Reports**: JSON and console output with key insights
- **Actionable Recommendations**: Supply chain and market impact analysis
- **Export Capabilities**: CSV and JSON data exports

## Current Status
✅ **ENTERPRISE-READY MULTI-COMMODITY SYSTEM**

### Successfully Processed Data
- **1,655+ weeks** of ESR data across **all 7 wheat commodity classes**
- **10-year historical coverage** (2017-2026) with **5-year statistical baselines**
- **Complete multi-commodity analysis** with comparative performance rankings

### Current Analysis Results (Week 22, MY 2026)
**All Wheat (MY 2026):**
- Current pace: **+31.5%** ahead of 5-year average
- Cumulative exports: **11.58M MT** (47.3% of USDA target)
- Total commitments: **16.80M MT** (68.6% of target)
- Outstanding sales: **5.23M MT** (forward pipeline)
- USDA full season target: **24.49M MT**

**Individual Wheat Grade Performance:**
- **Hard Red Winter**: 4.64M MT (40.1% of total)
- **Hard Red Spring**: 2.94M MT (25.4% of total)
- **White Wheat**: 2.16M MT (18.6% of total)
- **Soft Red Winter**: 1.64M MT (14.2% of total)
- **Durum Wheat**: 0.19M MT (1.6% of total)

## Technical Solutions

### Authentication
- USDA ESR API requires API key as query parameter (not headers)
- Environment variable support via `.env` file

### Data Quality Issues Resolved
- NaN/infinity value handling for SQLite compatibility
- Numpy type conversion for database parameter binding
- Marketing week calculation formula corrections

### Visualization Fixes
- Plotly API compatibility using layout dictionary approach
- Interactive dashboard generation for pace trends

## Usage

### Basic ETL
```bash
python main.py --commodity-code 107 --output output/wheat_exports.csv
```

### Multi-Commodity Dashboard (Current)
```bash
python enhanced_wheat_comparison.py
```

### Historical Data Collection
```bash
python fetch_historical_data.py
```

### Batch ETL Processing
```bash
python batch_etl.py
```

## Output Files
- `output/enhanced_wheat_multi_commodity_comparison.html` - Multi-commodity dashboard with pace analysis
- `output/wheat_exports.csv` - Raw export data
- `data/esr_data.db` - SQLite database with all processed data

## Dashboard Features
- **Clean Projection Approach**: Simple dotted line to USDA target (complex modeling on backburner)
- **Multi-Panel Layout**: Pace analysis, sales pipeline, and commodity breakdown
- **McKinsey-Style Annotations**: Professional callouts with key insights
- **Bendigo Color Theme**: Consistent burgundy/red branding throughout
- **Interactive Charts**: Hover tooltips with detailed metrics

## Technical Debt & Next Steps

### Priority Issues (See ISSUES.md)
**HIGH Priority:**
- Centralize commodity mappings across files (#1)
- Refactor SQLite connection management (#2)
- Replace .iterrows() with vectorized operations (#3)

**MEDIUM Priority:**
- Add composite database index for performance (#7)
- Centralize setup_logging() function (#4)
- Add type hints to enhanced_wheat_comparison.py (#10)

### Future Enhancements
- Enhanced projection modeling (momentum-adjusted or commitments-based)
- Automated scheduling for regular updates
- Email/alert capabilities for significant pace deviations
- Expand to additional commodities (corn, soybeans, etc.)