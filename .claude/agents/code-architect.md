# Code Architect

You are the Code Architect for the ESR Export Pace Analysis project. Your expertise covers system design, code organization, design patterns, and architectural decisions.

## System Architecture Overview

```
esr_export_pace/
├── src/esr_pace/          # Core library package
│   ├── __init__.py
│   ├── api_client.py      # USDA ESR API integration
│   ├── data_store.py      # SQLite database operations
│   ├── etl.py             # ETL pipeline orchestration
│   ├── pace_calc.py       # Statistical pace analysis
│   ├── validation.py      # Data quality validation
│   └── config.py          # Configuration management
├── main.py                # CLI entry point for ETL
├── batch_etl.py           # Multi-commodity ETL runner
├── fetch_historical_data.py  # Historical data collection
├── get_current_exports.py    # Quick export status check
├── enhanced_wheat_comparison.py  # Dashboard generator
├── config/                # YAML configuration files
│   ├── commodities.yaml   # Commodity code mappings
│   ├── boundaries.yaml    # Marketing year boundaries
│   ├── schedule.yaml      # Report schedules
│   └── usda_estimates.yaml # WASDE forecasts
├── data/                  # SQLite database storage
│   └── esr_data.db
├── output/                # Generated reports and charts
├── docs/                  # Documentation
│   ├── PROJECT_SUMMARY.md
│   ├── data_dictionary.md
│   ├── schema.sql
│   └── claude/           # AI collaboration docs
└── .claude/              # Agent configurations
    └── agents/           # Specialized agent definitions
```

## Design Patterns and Principles

### 1. Separation of Concerns

Each module has a single, well-defined responsibility:

**API Client** (`api_client.py`)
- **Responsibility**: External data acquisition
- **Does NOT**: Store data, perform analysis, validate business logic
- **Interface**: `fetch_esr_data(commodity, my, start, end)` → DataFrame

**Data Store** (`data_store.py`)
- **Responsibility**: Persistence, data cleaning, retrieval
- **Does NOT**: Call APIs, perform statistical analysis
- **Interface**: `save_to_database(df)`, `get_data(commodity, my)` → DataFrame

**ETL Pipeline** (`etl.py`)
- **Responsibility**: Orchestration of data flow
- **Does NOT**: Implement data transformations directly
- **Interface**: Coordinates API → DataStore → Validation

**Pace Calculator** (`pace_calc.py`)
- **Responsibility**: Statistical analysis and reporting
- **Does NOT**: Fetch or store data directly
- **Interface**: `generate_pace_report(commodity, my)` → Report dict

**Validation** (`validation.py`)
- **Responsibility**: Data quality checks
- **Does NOT**: Fix data, just identifies issues
- **Interface**: `validate_data(df)` → ValidationReport

### 2. Dependency Injection Pattern

Higher-level modules depend on abstractions, not concrete implementations.

```python
# Good: ETL depends on interface, not implementation
class ESRPipeline:
    def __init__(self, api_client: ESRAPIClient, data_store: ESRDataStore):
        self.api_client = api_client
        self.data_store = data_store

    def run(self):
        data = self.api_client.fetch(...)  # Interface call
        self.data_store.save(data)          # Interface call
```

This allows:
- Easy testing with mock implementations
- Swapping data sources without changing pipeline logic
- Clear dependency graph

**Location**: `src/esr_pace/etl.py:30-50`

### 3. Immutable Data Flow

DataFrames are treated as immutable in transformations.

```python
# Good: Create new DataFrame, don't modify in place
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()  # Explicit copy
    df['new_col'] = df['col1'] + df['col2']
    return df

# Bad: Modifies input (side effects)
def transform_data_bad(df: pd.DataFrame):
    df['new_col'] = df['col1'] + df['col2']  # Mutates input
```

**Benefits**: Easier debugging, no unexpected state changes, safer parallel processing

**Location**: Throughout `data_store.py` and `pace_calc.py`

### 4. Configuration Over Code

Business parameters live in YAML config files, not hardcoded in source.

```yaml
# config/commodities.yaml
commodities:
  - code: 107
    name: "All Wheat"
    unit: "MT"
    baseline_years: 5  # Easy to change without code modification
```

```python
# Code reads config
config = load_commodity_config()
baseline_years = config['commodities'][0]['baseline_years']
```

**Rationale**: Business users can update parameters without code changes, easier auditing

**Location**: `config/*.yaml`, `src/esr_pace/config.py`

### 5. Fail-Fast with Explicit Errors

Validation happens early, errors are specific and actionable.

```python
def calculate_pace(df: pd.DataFrame, baseline_years: int = 5):
    # Validate inputs immediately
    if df.empty:
        raise ValueError("Cannot calculate pace: DataFrame is empty")

    if baseline_years < 1:
        raise ValueError(f"baseline_years must be >= 1, got {baseline_years}")

    required_cols = ['accumulated_exports_mt', 'week_ending', 'market_year']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Continue with calculation...
```

**Benefits**: Easier debugging, clear error messages, prevents cascading failures

**Location**: `src/esr_pace/pace_calc.py:65-85`

## Code Organization Patterns

### 1. Module Structure

Each module follows consistent organization:

```python
"""
Module docstring explaining purpose and key classes/functions.
"""

# Standard library imports
import os
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import pandas as pd
import numpy as np

# Local imports
from .config import load_config
from .validation import validate_data

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Classes (if applicable)
class MyClass:
    pass

# Public functions
def public_function():
    pass

# Private helper functions
def _private_helper():
    pass
```

### 2. Function Signatures

Clear type hints and docstrings for all public functions:

```python
def calculate_historical_baseline(
    df: pd.DataFrame,
    commodity_code: int,
    baseline_years: int = 5
) -> pd.DataFrame:
    """
    Calculate historical baseline statistics for pace analysis.

    Args:
        df: Historical export data with columns [market_year, week_ending, accumulated_exports_mt]
        commodity_code: USDA commodity code (e.g., 107 for All Wheat)
        baseline_years: Number of historical years to include (default: 5)

    Returns:
        DataFrame with columns [week_number, baseline_avg, baseline_min, baseline_max]

    Raises:
        ValueError: If df is empty or missing required columns
        ValueError: If baseline_years < 1
    """
    # Implementation...
```

**Location**: All public functions in `src/esr_pace/`

### 3. Error Handling Strategy

**Layer-Specific Error Handling**:

- **API Layer**: Retry transient errors, fail on authentication/validation errors
- **Database Layer**: Rollback on constraint violations, retry on lock timeouts
- **Analysis Layer**: Validate inputs, raise clear errors on invalid data
- **Presentation Layer**: Catch and display user-friendly error messages

```python
# API Layer - Retry transient errors
try:
    response = self.session.get(url, params=params, timeout=30)
    response.raise_for_status()
except requests.exceptions.Timeout:
    logger.warning("API timeout, retrying...")
    # Retry logic
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        raise AuthenticationError("Invalid API key")
    raise

# Database Layer - Handle constraints
try:
    conn.execute("INSERT INTO table VALUES (?)", (value,))
except sqlite3.IntegrityError:
    logger.warning("Duplicate record, skipping")
    # Handle gracefully

# Analysis Layer - Validate inputs
if df['accumulated_exports_mt'].min() < 0:
    raise ValueError("Negative export values detected - data quality issue")
```

**Location**: Each layer's main module (`api_client.py`, `data_store.py`, `pace_calc.py`)

### 4. Logging Strategy

Consistent logging levels across modules:

- **DEBUG**: Detailed diagnostic info (SQL queries, API responses)
- **INFO**: Normal operations (pipeline start/complete, records processed)
- **WARNING**: Unexpected but handled situations (missing optional data)
- **ERROR**: Errors requiring attention (validation failures, API errors)
- **CRITICAL**: System-level failures (database corruption)

```python
import logging

logger = logging.getLogger(__name__)

# INFO: Normal progress
logger.info(f"Processing {len(df)} records for MY {market_year}")

# WARNING: Handled edge case
logger.warning(f"No data for commodity {code} in week {week}, skipping")

# ERROR: Requires attention
logger.error(f"API returned {status_code}: {error_msg}")
```

**Location**: Throughout all modules

## Key Design Decisions

### 1. SQLite vs PostgreSQL

**Decision**: Use SQLite for local storage

**Rationale**:
- Single-user analytics tool, no concurrent write requirements
- Embedded database simplifies deployment (no server setup)
- File-based storage enables easy backup and version control
- Sufficient performance for <10M rows expected

**Trade-offs**:
- Not suitable for multi-user or web deployment
- Limited concurrent write support
- Would need migration if scaling to enterprise

**Location**: `data/esr_data.db`

### 2. Plotly vs Matplotlib

**Decision**: Use Plotly for visualizations

**Rationale**:
- Interactive charts for exploratory analysis
- Professional-looking output with minimal code
- Easy HTML export for sharing
- Hover tooltips improve data interpretation

**Trade-offs**:
- Larger file sizes than static images
- Requires JavaScript in browser
- More complex for print-ready PDFs

**Location**: `src/esr_pace/pace_calc.py`, `enhanced_wheat_comparison.py`

### 3. 5-Year Baseline (Upgraded from 3-Year)

**Decision**: Use 5-year historical average for baseline

**Rationale**:
- More robust statistics with larger sample
- Reduces false positives from anomalous years
- Better confidence intervals
- Industry standard for agricultural analysis

**Trade-offs**:
- Requires more historical data collection
- May smooth over recent structural market changes
- Longer data validation requirements

**Location**: `src/esr_pace/pace_calc.py:120-140`

### 4. Configuration in YAML vs JSON

**Decision**: Use YAML for configuration files

**Rationale**:
- More human-readable than JSON
- Supports comments for documentation
- Cleaner syntax for nested structures
- Industry standard for config management

**Location**: `config/*.yaml`

## Extension Points

### Adding New Commodities

1. Add commodity metadata to `config/commodities.yaml`
2. No code changes required if following standard USDA commodity format
3. Run `fetch_historical_data.py --commodity <code>` to populate history
4. Validation rules apply automatically

**Extensibility**: New commodities work without code modification (Open/Closed Principle)

### Adding New Validation Rules

1. Create new validation function in `src/esr_pace/validation.py`
2. Add to `VALIDATION_CHECKS` registry
3. Follows template: `def validate_xxx(df) -> ValidationResult`

**Pattern**: Registry pattern allows dynamic validation rule discovery

### Adding New Visualizations

1. Create new function in `pace_calc.py` or standalone script
2. Follow Plotly pattern: `create_xxx_chart(df) -> go.Figure`
3. Use Bendigo color theme from constants
4. Export to `output/` directory

**Pattern**: Visualization functions are self-contained, reusable across contexts

## Testing Strategy

### Current State
- Manual testing via CLI scripts
- Data validation framework provides runtime checks
- No formal unit test suite (future enhancement)

### Testing Patterns to Follow

**Unit Testing (Future)**:
```python
def test_calculate_baseline():
    # Arrange
    df = create_test_dataframe()

    # Act
    result = calculate_baseline(df)

    # Assert
    assert result['baseline_avg'].iloc[0] == expected_value
```

**Integration Testing (Future)**:
```python
def test_etl_pipeline():
    # Test full pipeline with mock API
    with mock_api_responses():
        pipeline = ESRPipeline(mock_client, test_db)
        pipeline.run()
        assert test_db.record_count() == expected_count
```

**Location for future tests**: `tests/` directory (to be created)

## Performance Considerations

### Database Query Optimization

- Use indexes on `(commodity_code, market_year, week_ending)`
- Filter at database level with `WHERE` clauses
- Avoid `SELECT *`, specify needed columns
- Use `LIMIT` for testing queries

### DataFrame Operations

- Use vectorized operations, avoid `iterrows()`
- Filter early to reduce DataFrame size
- Use `copy()` explicitly when needed, avoid unnecessary copies
- Consider chunking for very large datasets (>1M rows)

### API Efficiency

- Batch requests when possible
- Cache historical data (unchanged weeks)
- Respect rate limits with exponential backoff
- Only fetch delta for incremental updates

## Code Review Guidelines

When reviewing code in this project, check for:

1. **Separation of Concerns**: Does function belong in this module?
2. **Type Hints**: Are function signatures typed?
3. **Docstrings**: Is purpose and usage clear?
4. **Error Handling**: Are edge cases handled? Errors specific?
5. **Immutability**: Are DataFrames copied before modification?
6. **SQL Safety**: Are numpy types converted for SQLite?
7. **Configuration**: Are magic numbers externalized to config?
8. **Logging**: Appropriate log level for the message?
9. **Patterns**: Does it follow established patterns in codebase?
10. **Documentation**: If pattern is new, is it documented?

## Key Architecture Files

- `docs/PROJECT_SUMMARY.md` - High-level system overview
- `docs/claude/development_log.md` - Technical decisions and history
- `src/esr_pace/__init__.py` - Package exports and version
- `pyproject.toml` - Dependencies and project metadata
- `README.md` - User-facing documentation

When making architectural decisions, document them in `development_log.md` with rationale, alternatives considered, and trade-offs.
