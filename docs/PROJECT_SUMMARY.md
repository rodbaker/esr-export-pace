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
   - 3-year historical baseline calculations
   - Statistical deviation analysis with confidence intervals
   - Interactive Plotly dashboards and visualizations
   - Comprehensive reporting with insights and recommendations

## Key Features

### Data Processing
- **Marketing Year Support**: June 1 - May 31 agricultural cycles
- **World Aggregation**: Country-level data rolled up to world totals
- **Historical Analysis**: 3+ years of baseline data for trend analysis
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

### Current Analysis Results
**All Wheat (MY 2026):**
- Current pace: **+26.19%** ahead of 5-year average
- **8/11 weeks** ahead of historical pace
- **4.6M MT** cumulative exports with strong forward sales

**Individual Wheat Grade Performance:**
- **Durum Wheat**: +162.5% ahead (exceptional performance)
- **Soft Red Winter**: +15.6% ahead (strong performance)
- **Hard Red Winter**: -22.8% behind (underperforming)
- **Complete dashboards** available for all wheat classes

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

### Pace Analysis
```bash
python test_pace_analysis.py
```

### Historical Data Collection
```bash
python fetch_historical_data.py
```

## Output Files
- `output/pace_analysis_report.json` - Complete analysis results
- `output/pace_analysis_107_2025.html` - Interactive pace chart
- `output/pace_dashboard_107_2025.html` - Executive dashboard
- `output/wheat_exports.csv` - Raw export data

## Next Steps
- Consider expanding to additional commodities
- Implement automated scheduling for regular updates
- Add email/alert capabilities for significant pace deviations
- Explore machine learning for export forecasting