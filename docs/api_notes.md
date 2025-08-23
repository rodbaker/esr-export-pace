# USDA ESR API - Implementation Notes

## Base Configuration
- **Base URL**: `https://api.fas.usda.gov`
- **Authentication**: None required (public API)
- **Rate Limits**: Unknown/undocumented - use conservative approach
- **Data Format**: JSON responses
- **Timezone**: All timestamps appear to be UTC

## Endpoint Details

### 1. Data Release Information
**Endpoint**: `GET /api/esr/datareleasedates`

**Purpose**: Determine current marketing year and freshness for incremental updates

**Response Fields**:
```json
{
  "commodityCode": 107,
  "marketYearStart": "2024-06-01T00:00:00",
  "marketYearEnd": "2025-05-31T00:00:00", 
  "marketYear": 2025,
  "releaseTimeStamp": "2025-08-14T00:00:00"
}
```

**Key Gotchas**:
- `marketYear` represents the ending year (e.g., 2025 for 2024-2025 MY)
- `releaseTimeStamp` indicates when data was last updated - use for incremental refresh
- All wheat classes (101-107) typically have same MY boundaries and release timestamp
- Date format is ISO 8601 without timezone suffix (assume UTC)

**Error Handling**:
- Returns empty array `[]` if no data available
- May return partial results during maintenance windows

### 2. Weekly Export Data
**Endpoint**: `GET /api/esr/exports/commodityCode/{commodityCode}/allCountries/marketYear/{marketYear}`

**Purpose**: Retrieve all weekly export data for a commodity and marketing year

**Key Response Fields**:
```json
{
  "commodityCode": 107,
  "countryCode": 1220,
  "weeklyExports": 19800,
  "accumulatedExports": 145600,
  "outstandingSales": 50000,
  "grossNewSales": 25000,
  "currentMYNetSales": 25000,
  "currentMYTotalCommitment": 195600,
  "nextMYOutstandingSales": 0,
  "nextMYNetSales": 0,
  "unitId": 1,
  "weekEndingDate": "2024-06-06T00:00:00"
}
```

**Critical Implementation Notes**:

#### Country Aggregation
- API returns one row per country per week
- Must sum across all countries to get world totals for MVP
- Use `countryCode` field to group (ignore country names for aggregation)
- Include all country codes including "UNKNOWN" (code 2)

#### Data Types & Validation
- All export values can be `null` - treat as 0 for aggregation
- `unitId` should always be 1 (Metric Tons) for wheat commodities
- `weekEndingDate` should always be Thursday - validate this
- `currentMYTotalCommitment` should equal `accumulatedExports + outstandingSales`

#### Week Sequencing
- Weeks are not guaranteed to be sequential in response
- Some weeks may be missing (no activity)
- Always sort by `weekEndingDate` after fetching
- First week may not start exactly on marketing year start date

**Error Scenarios**:
- Returns empty array `[]` for invalid commodity/year combinations
- May return partial data during ESR publication windows (Thursday 8:30 AM ET)
- HTTP 404 for future marketing years not yet available

### 3. Reference Data (Less Critical)

#### Countries
**Endpoint**: `GET /api/esr/countries`
- Use for country name lookups only
- `countryDescription` is display name
- `countryCode` is what appears in export data
- `regionId` maps to regions for future regional analysis

#### Commodities  
**Endpoint**: `GET /api/esr/commodities`
- Validate commodity codes exist
- Confirm `unitId` expectations
- Get proper display names

## API Client Implementation Guidelines

### Retry Strategy
```python
# Recommended backoff strategy
max_retries = 3
base_delay = 1.0  # seconds
backoff_factor = 2.0
jitter = True
```

**Retry Conditions**:
- HTTP 5xx errors (server errors)
- HTTP 429 (rate limited) 
- Connection timeouts
- DNS resolution failures

**Do NOT Retry**:
- HTTP 4xx errors (except 429)
- Invalid JSON responses
- Empty arrays (may be valid response)

### Request Headers
```python
headers = {
    'User-Agent': 'ESR-Export-Pace-Tracker/1.0',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache'
}
```

### Timeout Configuration
- **Connection timeout**: 10 seconds
- **Read timeout**: 30 seconds
- ESR data can be large (1000+ records per commodity/year)

### Concurrency Limits
- **Single-threaded requests only** (conservative approach)
- Add 1-2 second delay between requests to be respectful
- No parallel fetching until rate limits are documented

## Data Quality Observations

### Known Data Issues
1. **Revisions**: Accumulated exports get revised retroactively
2. **Late Reports**: Some weeks may appear days after ESR publication
3. **Country Mapping**: Country codes occasionally change (rare)
4. **Holiday Weeks**: ESR may skip publication during US holidays

### Validation Checkpoints
1. Verify all records have `unitId = 1` for wheat
2. Check `weekEndingDate` is Thursday (weekday = 3 in Python)
3. Validate dates fall within marketing year boundaries
4. Confirm arithmetic: `totalCommitment = accumulated + outstanding`
5. Check for logical progression in accumulated exports (should increase or stay same)

### Missing Data Handling
- If recent weeks missing: Log warning, continue with available data
- If entire commodity missing: Fail with clear error message
- If partial countries missing: Use available countries, log which are missing

## Incremental Update Strategy

### Freshness Detection
1. Call `/datareleasedates` for target commodity
2. Compare `releaseTimeStamp` with stored value in `dim_metadata`
3. If newer: fetch all data for current marketing year
4. If same: skip fetch, use cached data

### Update Frequency
- **Optimal**: Thursday afternoons after 9 AM ET (post-ESR publication)
- **Minimum**: Weekly
- **Maximum**: Daily (to catch revisions)

### Error Recovery
- If API fails: Keep last successful dataset, log error
- If partial data returned: Update available records, flag incomplete
- If significant data discrepancy: Alert and require manual review

## Testing & Validation Endpoints

### Quick Validation Call
```bash
# Test basic connectivity
curl "https://api.fas.usda.gov/api/esr/commodities" | jq '.[0:3]'

# Test specific commodity data availability  
curl "https://api.fas.usda.gov/api/esr/datareleasedates" | jq '.[] | select(.commodityCode == 107)'
```

### Sample Data Ranges
- **All Wheat (107)**: Data available from ~1990 to current
- **Current MY**: Always available, updated weekly
- **Historical**: Stable after marketing year completion