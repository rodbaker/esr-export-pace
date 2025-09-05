# ESR Export Pace Analysis - Quick Reference

## 🚀 Environment Setup
```bash
# Activate virtual environment (required for each session)
source /home/roddyb/.cache/pypoetry/virtualenvs/esr-export-pace-bkV0cXP8-py3.10/bin/activate

# Alternative: Use Poetry prefix for all commands
poetry run python main.py
```

## 📊 Core Commands

### Single Commodity Analysis
```bash
# Process All Wheat (default)
python main.py --force-refresh

# Process specific wheat class
python main.py --commodity-code 101 --force-refresh  # Hard Red Winter
python main.py --commodity-code 105 --force-refresh  # Durum

# List available commodities
python main.py --list-commodities
```

### Batch Processing
```bash
# Process all wheat classes
python batch_etl.py --force-refresh

# Process specific commodities
python batch_etl.py --include "101,102,107" --force-refresh

# Exclude specific commodities
python batch_etl.py --exclude "106" --force-refresh

# Dry run (see what would be processed)
python batch_etl.py --dry-run --include "101,103"
```

### Historical Data Collection
```bash
# Collect 10 years of data for all commodities
python fetch_historical_data.py --years 2017 2018 2019 2020 2021 2022

# Specific commodities and years
python fetch_historical_data.py --commodities 101 102 107 --years 2020 2021 2022

# Single commodity with verbose logging
python fetch_historical_data.py --commodity 107 --years 2017 2018 2019 --verbose
```

### Analysis & Reporting
```bash
# Generate pace analysis for All Wheat
python test_pace_analysis.py

# Analyze specific wheat grade
python analyze_wheat_grade.py 101  # Hard Red Winter

# Compare performance across all grades
python compare_wheat_grades.py

# Get current export totals by grade
python get_current_exports.py
```

## 🌾 Wheat Commodity Codes
- **101**: Hard Red Winter Wheat
- **102**: Soft Red Winter Wheat  
- **103**: Hard Red Spring Wheat
- **104**: White Wheat
- **105**: Durum Wheat
- **106**: Mixed Wheat
- **107**: All Wheat (aggregate)

## 📁 Key Files & Directories
```
├── main.py                    # Single commodity ETL
├── batch_etl.py              # Multi-commodity batch processing
├── fetch_historical_data.py  # Historical data collection
├── analyze_wheat_grade.py    # Individual grade analysis
├── compare_wheat_grades.py   # Cross-grade comparison
├── get_current_exports.py    # Current totals
├── data/                     # CSV exports
├── output/                   # Charts and visualizations
└── src/esr_pace/            # Core modules
```

## 🔧 Environment Variables
```bash
# Optional: Set USDA API key for better rate limits
export USDA_ESR_API_KEY=your_key_here

# Or add to .env file
echo "USDA_ESR_API_KEY=your_key_here" >> .env
```

## 📈 Current Status (MY 2026)
- **All Wheat**: 26.2% ahead of 5-year average
- **8/11 weeks** ahead of pace
- **4.6M MT** current exports
- **Top performer**: Durum (+162.5%)
- **Underperformer**: Hard Red Winter (-22.8%)

## 🛠️ Troubleshooting
```bash
# Check Python/Poetry status
python --version              # Should work after activation
poetry env info              # Show virtual environment details

# Check database status  
ls -la data/                 # Check for CSV files
sqlite3 data/esr_exports.db ".tables"  # Check database tables

# Check logs
tail -f esr_etl.log          # Monitor ETL pipeline
tail -f esr_historical_fetch.log  # Monitor historical data collection

# Run tests
python test_multi_commodity.py  # Validate multi-commodity system
```

## 🎯 Quick Start Workflow
1. **Activate environment**: `source /home/roddyb/.cache/pypoetry/virtualenvs/esr-export-pace-bkV0cXP8-py3.10/bin/activate`
2. **Test single commodity**: `python main.py --commodity-code 107 --force-refresh`
3. **Run batch collection**: `python batch_etl.py --force-refresh`
4. **Generate analysis**: `python compare_wheat_grades.py`
5. **View results**: Check `output/` and `data/` directories

## 📊 Output Files
- **CSV Exports**: `data/commodity_{code}_exports.csv`
- **Charts**: `output/wheat_historical_range_chart.html`
- **Analysis**: Generated JSON reports and summaries

---
*Generated for quick reference when returning to the ESR Export Pace Analysis project*