# ESR Export Pace Analysis

A comprehensive system for analyzing US agricultural export performance using USDA Export Sales Reporting (ESR) data. Track export pace against historical baselines with advanced statistical analysis and interactive visualizations.

## 🌾 Features

- **Complete ETL Pipeline**: Automated data extraction from USDA ESR API
- **Pace Analysis Engine**: Compare current exports vs 3-year historical averages
- **Statistical Insights**: Z-scores, confidence intervals, outlier detection
- **Interactive Visualizations**: Historical range charts and pace dashboards
- **Data Validation**: 14+ validation checks for data quality assurance
- **Comprehensive Reporting**: JSON exports and executive summaries

## 📊 Visualizations

### Historical Range Chart
Shows current marketing year performance against historical high/low ranges:
- Gray shaded area: Historical min/max range
- Red dashed line: Historical average
- Blue line: Current marketing year actual exports
- Smart annotations for performance assessment

### Pace Analysis Dashboard
Multi-panel view with:
- Cumulative exports vs historical baseline
- Weekly pace deviations with severity bands
- Performance distribution histogram
- Key performance indicators

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Poetry (for dependency management)
- USDA ESR API key (optional but recommended)

### Installation
```bash
git clone https://github.com/yourusername/esr-export-pace.git
cd esr-export-pace
poetry install
```

### Configuration
```bash
# Add your USDA ESR API key (optional)
echo "USDA_ESR_API_KEY=your_key_here" >> .env
```

### Basic Usage
```bash
# Run ETL pipeline for All Wheat (commodity 107)
python main.py --commodity-code 107 --output output/wheat_exports.csv

# Generate pace analysis report
python test_pace_analysis.py

# Create historical range chart
python test_range_chart.py
```

## 🏗️ Architecture

```
src/esr_pace/
├── api_client.py      # USDA ESR API integration
├── data_store.py      # SQLite database operations
├── etl.py             # ETL pipeline orchestration
├── pace_calc.py       # Statistical pace analysis
└── validation.py      # Data quality validation
```

## 📈 Current Analysis Results

**Latest Wheat Export Analysis (MY 2026):**
- **26.2%** ahead of 3-year historical average
- **8/11 weeks** ahead of pace
- **High volatility** score: 1.70
- **3 statistical outliers** detected
- Strong forward sales position

## 🛠️ Key Technical Solutions

### API Authentication
- USDA ESR API requires API key as query parameter (not headers)
- Exponential backoff retry logic for reliability

### Data Quality
- Comprehensive data cleaning for SQLite compatibility
- Numpy type conversion for database operations
- Marketing week calculation using Julian date arithmetic

### Marketing Year Logic
- Agricultural year cycles: June 1 - May 31
- Proper handling of cross-calendar-year periods
- Week-by-week accumulation tracking

## 📊 Database Schema

SQLite database with two main tables:
- `fact_esr_world_weekly`: Weekly export data with world-level aggregation
- `dim_metadata`: Analysis metadata and run history

## 🔍 Validation Framework

14+ validation checks across categories:
- **Structural**: Column presence, data types, date formats
- **Arithmetic**: Non-negative values, accumulation consistency
- **Business Logic**: Marketing year boundaries, seasonal patterns

## 📚 Documentation

- `docs/PROJECT_SUMMARY.md`: Complete system overview
- `docs/claude/development_log.md`: Technical implementation details
- `docs/claude/subagent_guidelines.md`: AI collaboration patterns
- `docs/api_notes.md`: USDA ESR API reference
- `docs/data_dictionary.md`: Field definitions and business rules

## 🤖 AI-Assisted Development

This project was developed with Claude Code, demonstrating effective human-AI collaboration patterns:
- Systematic problem decomposition
- Technical challenge resolution
- Code review and optimization
- Documentation generation

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Support

For questions or issues, please open a GitHub issue or contact the maintainers.

---

**Developed with Claude Code** - Demonstrating the power of human-AI collaboration in agricultural data analysis.
