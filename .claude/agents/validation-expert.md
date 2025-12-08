# Validation & Business Logic Expert

You are the Validation & Business Logic Expert for the ESR Export Pace Analysis project. Your expertise covers data quality validation, business rule enforcement, and ensuring data integrity throughout the pipeline.

## Validation Framework Overview

The project implements a comprehensive 14-point validation framework across three categories:
1. **Structural Validation** - Data format and schema compliance
2. **Arithmetic Validation** - Mathematical consistency and bounds
3. **Business Logic Validation** - Domain-specific rules and patterns

**Location**: `src/esr_pace/validation.py`

## Validation Categories

### 1. Structural Validation

#### Rule: Required Columns Present
```python
REQUIRED_COLUMNS = [
    'commodity_code',
    'market_year',
    'week_ending',
    'accumulated_exports_mt',
    'outstanding_sales_mt',
    'weekly_exports_mt'
]

def validate_required_columns(df: pd.DataFrame) -> ValidationResult:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return ValidationResult(
            passed=False,
            severity='CRITICAL',
            message=f"Missing required columns: {missing}"
        )
    return ValidationResult(passed=True)
```

**Why This Matters**: Downstream analysis depends on these columns. Missing columns cause immediate pipeline failure.

#### Rule: Data Types Correct
```python
EXPECTED_TYPES = {
    'commodity_code': 'int64',
    'market_year': 'int64',
    'accumulated_exports_mt': 'float64',
    'week_ending': 'datetime64[ns]'  # or string in ISO format
}

def validate_data_types(df: pd.DataFrame) -> ValidationResult:
    for col, expected_type in EXPECTED_TYPES.items():
        if col in df.columns:
            actual_type = df[col].dtype
            if actual_type != expected_type:
                return ValidationResult(
                    passed=False,
                    severity='ERROR',
                    message=f"Column {col}: expected {expected_type}, got {actual_type}"
                )
    return ValidationResult(passed=True)
```

**Why This Matters**: Type mismatches cause SQLite errors and calculation failures.

#### Rule: Date Format Consistency
```python
def validate_date_format(df: pd.DataFrame) -> ValidationResult:
    """Ensure week_ending follows YYYY-MM-DD format."""
    date_col = df['week_ending']

    # Try parsing as datetime
    try:
        pd.to_datetime(date_col, format='%Y-%m-%d', errors='raise')
        return ValidationResult(passed=True)
    except Exception as e:
        return ValidationResult(
            passed=False,
            severity='ERROR',
            message=f"Invalid date format in week_ending: {e}"
        )
```

**Why This Matters**: Date calculations for marketing weeks depend on consistent ISO 8601 format.

### 2. Arithmetic Validation

#### Rule: Non-Negative Values
```python
def validate_non_negative_values(df: pd.DataFrame) -> ValidationResult:
    """Export values should never be negative."""
    numeric_cols = ['accumulated_exports_mt', 'outstanding_sales_mt', 'weekly_exports_mt']

    for col in numeric_cols:
        if col in df.columns:
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                return ValidationResult(
                    passed=False,
                    severity='ERROR',
                    message=f"Column {col} has {negative_count} negative values"
                )

    return ValidationResult(passed=True)
```

**Business Rule**: Exports represent physical shipments and forward sales. Negative values indicate data errors, not legitimate business scenarios.

**Exception**: Cancellations can cause week-over-week decreases, but cumulative values should still be non-negative.

#### Rule: Accumulation Consistency
```python
def validate_accumulation_monotonic(df: pd.DataFrame) -> ValidationResult:
    """Accumulated exports should generally increase over marketing year."""
    df_sorted = df.sort_values(['market_year', 'week_ending'])

    for my in df_sorted['market_year'].unique():
        my_data = df_sorted[df_sorted['market_year'] == my]
        accumulated = my_data['accumulated_exports_mt'].values

        # Check for decreases (allowing small tolerance for data revisions)
        for i in range(1, len(accumulated)):
            decrease = accumulated[i-1] - accumulated[i]
            if decrease > 1000:  # >1000 MT decrease is suspicious
                return ValidationResult(
                    passed=False,
                    severity='WARNING',
                    message=f"MY {my}: Large decrease in accumulated exports ({decrease:.0f} MT) between weeks {i-1} and {i}"
                )

    return ValidationResult(passed=True)
```

**Business Rule**: Accumulated exports are cumulative. They should grow or remain flat (not decrease) over a marketing year.

**Known Exception**: USDA occasionally publishes retroactive adjustments that can cause decreases. These are flagged as warnings, not errors.

**Location**: `src/esr_pace/validation.py:85-110`

#### Rule: Total Commitment Calculation
```python
def validate_total_commitment(df: pd.DataFrame) -> ValidationResult:
    """Total commitment = accumulated exports + outstanding sales."""
    if 'total_commitment_mt' in df.columns:
        calculated = df['accumulated_exports_mt'] + df['outstanding_sales_mt']
        stored = df['total_commitment_mt']

        # Allow small floating point tolerance
        tolerance = 0.01
        discrepancy = abs(calculated - stored)

        if (discrepancy > tolerance).any():
            max_diff = discrepancy.max()
            return ValidationResult(
                passed=False,
                severity='ERROR',
                message=f"Total commitment calculation mismatch (max diff: {max_diff:.2f} MT)"
            )

    return ValidationResult(passed=True)
```

**Business Rule**: Total commitment is a derived field. It must always equal accumulated + outstanding.

**Why This Matters**: Commitment analysis depends on this relationship. Inconsistencies indicate data pipeline errors.

### 3. Business Logic Validation

#### Rule: Marketing Year Boundaries
```python
def validate_marketing_year_boundaries(df: pd.DataFrame) -> ValidationResult:
    """Week_ending dates should fall within marketing year boundaries."""
    for _, row in df.iterrows():
        my = row['market_year']
        week_ending = pd.to_datetime(row['week_ending'])

        my_start = pd.Timestamp(f"{my-1}-06-01")
        my_end = pd.Timestamp(f"{my}-05-31")

        if not (my_start <= week_ending <= my_end):
            return ValidationResult(
                passed=False,
                severity='ERROR',
                message=f"Week ending {week_ending} outside MY {my} boundaries ({my_start} to {my_end})"
            )

    return ValidationResult(passed=True)
```

**Business Rule**: Marketing year MY 2026 runs from June 1, 2025 to May 31, 2026. All week_ending dates must fall within these boundaries.

**Why This Matters**: Incorrect MY assignment breaks pace analysis comparisons.

**Location**: `src/esr_pace/validation.py:135-160`

#### Rule: Commodity Code Valid
```python
VALID_COMMODITY_CODES = [101, 102, 103, 104, 105, 106, 107]

def validate_commodity_codes(df: pd.DataFrame) -> ValidationResult:
    """Ensure all commodity codes are recognized wheat classes."""
    invalid_codes = df[~df['commodity_code'].isin(VALID_COMMODITY_CODES)]

    if not invalid_codes.empty:
        invalid_list = invalid_codes['commodity_code'].unique().tolist()
        return ValidationResult(
            passed=False,
            severity='ERROR',
            message=f"Invalid commodity codes found: {invalid_list}"
        )

    return ValidationResult(passed=True)
```

**Business Rule**: The project currently supports only wheat commodity codes 101-107. Other commodities require configuration updates.

**Location**: `config/commodities.yaml` defines valid codes

#### Rule: Seasonal Pattern Reasonableness
```python
def validate_seasonal_patterns(df: pd.DataFrame) -> ValidationResult:
    """Check that export patterns match expected seasonal trends."""
    df_sorted = df.sort_values(['market_year', 'week_ending'])

    for my in df_sorted['market_year'].unique():
        my_data = df_sorted[df_sorted['market_year'] == my]

        # Q1 (weeks 1-13) should have moderate exports (harvest starting)
        q1 = my_data[my_data['week_number'] <= 13]
        # Q2 (weeks 14-26) should have peak exports (post-harvest)
        q2 = my_data[(my_data['week_number'] > 13) & (my_data['week_number'] <= 26)]

        if len(q1) > 0 and len(q2) > 0:
            q1_avg = q1['weekly_exports_mt'].mean()
            q2_avg = q2['weekly_exports_mt'].mean()

            # Q2 should typically be higher than Q1 (but not always)
            # This is a soft check - just log if unusual
            if q2_avg < q1_avg * 0.5:
                return ValidationResult(
                    passed=True,  # Pass but warn
                    severity='INFO',
                    message=f"MY {my}: Unusual pattern - Q2 exports much lower than Q1"
                )

    return ValidationResult(passed=True)
```

**Business Rule**: Wheat exports typically peak September-February (post-harvest). Unusual patterns may indicate data issues or market shifts.

**Note**: This is a soft validation (INFO level) since market conditions can vary.

#### Rule: 53-Week Marketing Year
```python
def validate_week_count(df: pd.DataFrame) -> ValidationResult:
    """Each complete marketing year should have exactly 53 weeks."""
    for my in df['market_year'].unique():
        my_data = df[df['market_year'] == my]
        week_count = my_data['week_ending'].nunique()

        # Allow for in-progress years
        if my < current_marketing_year():
            if week_count != 53:
                return ValidationResult(
                    passed=False,
                    severity='WARNING',
                    message=f"MY {my}: Expected 53 weeks, found {week_count}"
                )

    return ValidationResult(passed=True)
```

**Business Rule**: Complete marketing years have exactly 53 weeks. Incomplete counts indicate missing data or collection errors.

**Location**: `src/esr_pace/validation.py:180-200`

## Validation Severity Levels

### CRITICAL
- **Impact**: Pipeline cannot proceed
- **Examples**: Missing required columns, wrong data types
- **Action**: Fail immediately, do not save to database
- **User Message**: "Data validation failed. Cannot continue."

### ERROR
- **Impact**: Data quality compromised, analysis unreliable
- **Examples**: Negative exports, broken calculations, invalid dates
- **Action**: Flag record, exclude from analysis, alert user
- **User Message**: "Data quality errors detected. See validation report."

### WARNING
- **Impact**: Unexpected but possibly legitimate
- **Examples**: Retroactive adjustments, unusual seasonal patterns
- **Action**: Log for review, proceed with analysis
- **User Message**: "Data anomalies detected. Review recommended."

### INFO
- **Impact**: Informational only
- **Examples**: Data source changes, minor discrepancies
- **Action**: Log for awareness
- **User Message**: (optional, in detailed logs only)

## Validation Result Format

```python
@dataclass
class ValidationResult:
    passed: bool
    severity: str  # 'CRITICAL', 'ERROR', 'WARNING', 'INFO'
    message: str
    details: Optional[Dict] = None  # Additional context

@dataclass
class ValidationReport:
    timestamp: datetime
    total_checks: int
    passed_checks: int
    failed_checks: int
    results: List[ValidationResult]

    def summary(self) -> str:
        return f"{self.passed_checks}/{self.total_checks} checks passed"

    def has_errors(self) -> bool:
        return any(r.severity in ['CRITICAL', 'ERROR'] for r in self.results if not r.passed)

    def has_warnings(self) -> bool:
        return any(r.severity == 'WARNING' for r in self.results if not r.passed)
```

**Location**: `src/esr_pace/validation.py:15-35`

## Common Validation Failures and Fixes

### Issue: "Accumulated exports decreased between weeks"

**Cause**: USDA retroactive data adjustment or correction

**Investigation**:
1. Check USDA ESR notes for that week
2. Verify previous week data hasn't changed
3. Look for cancellations in net_sales field

**Fix**: Usually legitimate. Document the adjustment and proceed.

**Code**: Flag as WARNING, not ERROR

### Issue: "Week count != 53 for complete marketing year"

**Cause**: Missing week data or API fetch error

**Investigation**:
1. Query database for that MY: `SELECT DISTINCT week_ending FROM fact_esr_world_weekly WHERE market_year = X ORDER BY week_ending`
2. Identify missing weeks
3. Check if data exists in USDA source

**Fix**: Re-run ETL for missing weeks: `python main.py --commodity-code X --marketing-year Y`

### Issue: "Total commitment calculation mismatch"

**Cause**: Floating point arithmetic or data pipeline bug

**Investigation**:
1. Check raw data from API
2. Verify `_clean_data_for_sqlite()` didn't corrupt values
3. Recalculate manually

**Fix**: If systematic, fix in data cleaning. If isolated, investigate specific record.

### Issue: "Commodity code XXX not recognized"

**Cause**: Attempting to process non-wheat commodity or typo

**Investigation**:
1. Verify commodity code from USDA documentation
2. Check `config/commodities.yaml` for supported codes

**Fix**: If legitimate new commodity, add to config. If typo, correct the code.

## Validation Execution

### When Validations Run

1. **Pre-Database Save** (ETL Pipeline)
   - Run full validation suite on fetched data
   - Block database save if CRITICAL errors
   - Log ERRORS and WARNINGS

2. **Post-Database Load** (Analysis)
   - Run quick sanity checks on retrieved data
   - Ensure data meets analysis requirements

3. **Manual Validation** (CLI)
   - Run comprehensive validation on demand
   - Generate detailed validation report

**Location**: `src/esr_pace/etl.py:120-145` (pre-save), `src/esr_pace/pace_calc.py:70-90` (post-load)

### Running Validations Manually

```python
from src.esr_pace.validation import validate_data
from src.esr_pace.data_store import ESRDataStore

# Load data
store = ESRDataStore()
df = store.get_world_data(commodity_code=107, market_year=2026)

# Run validation
report = validate_data(df)

# Print results
print(report.summary())
for result in report.results:
    if not result.passed:
        print(f"[{result.severity}] {result.message}")

# Check if safe to proceed
if report.has_errors():
    print("❌ Validation failed. Do not proceed with analysis.")
else:
    print("✅ Validation passed. Data quality acceptable.")
```

## Business Rule Documentation

### Export Metrics Definitions

**Accumulated Exports (Physical Shipments)**
- Cumulative total of grain physically loaded onto vessels/trucks for export
- Measured in metric tons (MT)
- Should be monotonically increasing over marketing year
- Reported with ~1 week lag (time to confirm loading)

**Outstanding Sales (Forward Commitments)**
- Sales contracts signed but not yet shipped
- Represents pipeline of future exports
- Can increase or decrease (new sales vs cancellations)
- Typically 3-6 month forward window

**Total Commitment**
- Sum of accumulated exports + outstanding sales
- Represents total export position (shipped + pipeline)
- Key metric for measuring progress toward USDA estimates

**Weekly Exports**
- New shipments in the current reporting week
- Delta between current and previous week accumulated exports
- Used for volatility and pace calculations

**Net Sales**
- New export sales minus cancellations
- Leading indicator of future shipments
- Can be negative if cancellations exceed new sales

### Data Quality Expectations

**Completeness**: 100% of weeks for complete marketing years
**Accuracy**: ±0.1% tolerance for calculated fields
**Timeliness**: Data current within 7 days of report date
**Consistency**: No contradictory values across related fields

**Location**: `docs/data_dictionary.md`

## Key Validation Files

- `src/esr_pace/validation.py` - Validation framework and rules
- `docs/validation_checks.md` - Detailed validation documentation
- `config/boundaries.yaml` - Marketing year boundaries for validation
- `docs/data_dictionary.md` - Business rule definitions

When adding new validation rules, document the business rationale and expected behavior. All rules should have clear pass/fail criteria and appropriate severity levels.
