# ESR Data Validation Checklist

## Pre-Processing Validation

### API Response Validation
- [ ] **HTTP Status**: Response code is 200
- [ ] **Content Type**: Response is valid JSON
- [ ] **Response Size**: Non-empty array returned
- [ ] **Required Fields**: All expected fields present in each record
- [ ] **Data Types**: Numeric fields are numbers, dates are valid ISO 8601

### Reference Data Consistency
- [ ] **Commodity Code**: Matches requested commodity in API call
- [ ] **Market Year**: Matches requested market year in API call  
- [ ] **Unit ID**: All records have `unitId = 1` (Metric Tons) for wheat
- [ ] **Country Codes**: All country codes are valid integers > 0

## Structural Data Validation

### Date & Time Validation
- [ ] **Thursday Dates**: All `weekEndingDate` values are Thursdays
- [ ] **Date Range**: All dates fall between `marketYearStart` and `marketYearEnd`
- [ ] **Date Sequence**: Week ending dates are in chronological order
- [ ] **Date Gaps**: No gaps > 14 days between consecutive weeks (allow for holidays)
- [ ] **Future Dates**: No dates beyond current date + 7 days

### Key Integrity
- [ ] **Primary Key**: No duplicate (commodity_code, market_year, week_ending) combinations
- [ ] **Country Coverage**: Each week has consistent set of reporting countries
- [ ] **Complete Weeks**: No partial week data (all countries report or none)

## Arithmetic Validation

### Field Logic Checks
- [ ] **Total Commitment**: `currentMYTotalCommitment = accumulatedExports + outstandingSales` (±0.01 tolerance)
- [ ] **Non-Negative Values**: `weeklyExports`, `accumulatedExports`, `outstandingSales` ≥ 0
- [ ] **Net Sales**: `currentMYNetSales` can be negative (cancellations allowed)
- [ ] **Accumulated Growth**: `accumulatedExports` is monotonic (non-decreasing) within marketing year

### Cross-Week Validation
- [ ] **Weekly Consistency**: `accumulatedExports[week_n] = accumulatedExports[week_n-1] + weeklyExports[week_n]`
- [ ] **Season Totals**: Final accumulated exports are reasonable vs. historical ranges
- [ ] **Outstanding Trends**: Outstanding sales follow logical patterns (high early, decrease toward MY end)

## Aggregation Validation

### World Total Calculations
- [ ] **Country Sum**: World totals equal sum of all country records per week
- [ ] **Missing Countries**: Identify if major importers are missing from any week
- [ ] **Unknown Countries**: Handle "UNKNOWN" country code (2) appropriately
- [ ] **Zero Weeks**: Weeks with zero activity across all countries are valid

### Data Completeness
- [ ] **Marketing Year Coverage**: Data spans full marketing year or reasonable partial coverage
- [ ] **Recent Weeks**: Current week or previous week data is present
- [ ] **Historical Continuity**: No unexplained gaps in weekly sequence

## Business Logic Validation

### Seasonal Patterns
- [ ] **Export Pace**: Current year pace falls within reasonable bounds vs. historical
- [ ] **Harvest Timing**: Higher exports align with typical post-harvest periods
- [ ] **Sales Timing**: New sales activity aligns with typical booking seasons
- [ ] **Outstanding Pattern**: Outstanding sales decrease as MY progresses

### Market Reality Checks
- [ ] **Volume Ranges**: Weekly exports between 0-5M MT (extreme check for wheat)
- [ ] **Annual Totals**: Marketing year totals align with USDA projections (±20%)
- [ ] **Country Shares**: Major importers have reasonable share of total trade
- [ ] **Revision Magnitude**: Changes from previous runs are reasonable (<10% typical)

## Error Handling Validation

### Data Quality Flags
- [ ] **Incomplete Weeks**: Flag weeks missing major importing countries
- [ ] **Revision Alerts**: Flag significant changes from previous data pulls
- [ ] **Outlier Detection**: Flag weekly exports >3 standard deviations from mean
- [ ] **Missing Data**: Flag commodities with no recent updates

### Recovery Procedures
- [ ] **Partial Failures**: System continues with available data when subset fails
- [ ] **API Errors**: Graceful handling of timeouts and HTTP errors
- [ ] **Data Corruption**: Detection and quarantine of corrupted records
- [ ] **Rollback Capability**: Can restore previous good dataset if needed

## Post-Processing Validation

### Database Integrity
- [ ] **Successful Insert**: All records inserted without constraint violations
- [ ] **Transaction Integrity**: Full week data committed atomically
- [ ] **Index Performance**: Database queries perform within acceptable time limits
- [ ] **Storage Size**: Database size growth is reasonable

### Export File Validation
- [ ] **CSV Format**: Properly formatted CSV with headers
- [ ] **File Completeness**: All database records present in export
- [ ] **Encoding**: UTF-8 encoding for international characters
- [ ] **File Size**: Reasonable file size for data volume

## Monitoring & Alerting

### Daily Health Checks
- [ ] **Data Freshness**: Most recent data within 7 days of current date
- [ ] **API Connectivity**: Successful API calls in last 24 hours
- [ ] **Processing Success**: ETL pipeline completed without errors
- [ ] **Storage Health**: Database and file system have adequate space

### Weekly Review Items
- [ ] **Pace Analysis**: Current pace vs. historical is reasonable
- [ ] **Data Coverage**: All enabled commodities have current data
- [ ] **Revision Impact**: Any significant revisions noted and explained
- [ ] **Performance**: Processing time within acceptable bounds

## Validation Implementation

### Automated Checks (Must Implement)
```python
def validate_structural(df):
    """Core structural validation - fail fast if these fail"""
    # Primary key uniqueness
    # Thursday dates
    # Unit ID consistency
    # Date range bounds

def validate_arithmetic(df):
    """Arithmetic validation - warn on failures"""
    # Total commitment math
    # Non-negative constraints  
    # Monotonic accumulated exports

def validate_business_logic(df):
    """Business rule validation - log warnings"""
    # Reasonable volume ranges
    # Seasonal pattern checks
    # Outlier detection
```

### Manual Review Triggers
- First run of new marketing year
- Significant changes in trading patterns
- API response format changes
- Large revisions to historical data

### Validation Reporting
- **Daily**: Automated validation summary in logs
- **Weekly**: Validation dashboard with key metrics
- **Monthly**: Comprehensive data quality report
- **Ad-hoc**: Validation report before major analysis