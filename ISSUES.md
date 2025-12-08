# Known Issues and Technical Debt

**Last Updated**: 2025-12-06
**Project**: ESR Export Pace Analysis

This document tracks known issues, technical debt, and future enhancements for the project. Issues are prioritized by severity and organized by category.

---

## 🔴 CRITICAL Issues

All critical issues have been resolved as of 2025-12-06.

---

## 🟠 HIGH Priority Issues

### #1: Centralize Commodity Mappings
**Status**: Open
**Priority**: HIGH
**Category**: Code Quality - DRY Violation

**Description**:
Commodity code-to-name mappings are duplicated in 3 locations:
1. `config/commodities.yaml` (authoritative source)
2. `enhanced_wheat_comparison.py` (WHEAT_COMMODITIES, WHEAT_SHORT_CODES, WHEAT_COLORS dicts)
3. `get_current_exports.py` (wheat_classes dictionary)

**Impact**:
- Violation of DRY (Don't Repeat Yourself) principle
- Risk of inconsistency if commodity names change
- Maintenance burden when adding new commodities

**Recommended Fix**:
Create centralized commodity mapping in `src/esr_pace/config.py`:

```python
from src.esr_pace.config import get_commodity_mappings

# In config.py
def get_commodity_mappings() -> Dict[int, Dict[str, str]]:
    """Load commodity mappings from YAML config."""
    config = load_config()
    return {
        c['code']: {
            'name': c['name'],
            'short_name': _get_short_code(c['code']),
            'color': _get_bendigo_color(c['code'])
        }
        for c in config.commodities if c['enabled']
    }
```

**Files to Modify**:
- `src/esr_pace/config.py` (add centralized functions)
- `enhanced_wheat_comparison.py` (remove hardcoded dicts, import from config)
- `get_current_exports.py` (remove hardcoded dict, import from config)

---

### #2: SQLite Connection Management Refactoring
**Status**: Open (Documented as TODO)
**Priority**: HIGH
**Category**: Technical - Resource Management

**Description**:
The `ESRDataStore` class maintains a persistent connection (`self.conn`) that is not properly managed with context managers. This can lead to:
- Connection leaks
- Database locks
- File descriptor exhaustion

**Impact**:
- Potential database corruption under load
- Resource leaks in long-running processes
- Hard-to-debug locking issues

**Recommended Fix**:
Refactor all database methods to use context managers:

```python
# Current pattern (risky)
def get_data(self):
    conn = self._get_connection()
    return pd.read_sql_query(query, conn)

# Improved pattern (safe)
def get_data(self):
    with sqlite3.connect(str(self.db_path)) as conn:
        return pd.read_sql_query(query, conn)
```

**Files to Modify**:
- `src/esr_pace/data_store.py` (all methods using `_get_connection()`)

**Current Status**:
- TODO comments added at lines 32-35 in `data_store.py`
- Full refactoring deferred to prevent breaking changes

---

### #3: Performance Anti-Pattern - `.iterrows()` Usage
**Status**: Open
**Priority**: HIGH
**Category**: Performance

**Description**:
Using `.iterrows()` for database operations is 10-100x slower than vectorized approaches.

**Locations**:
1. `src/esr_pace/data_store.py:247-252` (upsert DELETE loop)
2. `src/esr_pace/pace_calc.py:317` (pace calculation loop)

**Impact**:
- 10-100x performance penalty on data insertion
- Slower pace calculations, especially for full-year analysis
- Inefficient for historical batch loads

**Recommended Fix**:

```python
# data_store.py - Replace iterrows with executemany
delete_params = df[['commodity_code', 'market_year', 'week_ending']].values.tolist()
conn.executemany(
    """DELETE FROM fact_esr_world_weekly
       WHERE commodity_code = ? AND market_year = ? AND week_ending = ?""",
    delete_params
)

# pace_calc.py - Replace with vectorized operations
df_current['pace_deviation'] = (
    (df_current['accumulated_exports_mt'] - baseline_lookup['avg']) /
    baseline_lookup['avg'] * 100
)
```

**Files to Modify**:
- `src/esr_pace/data_store.py:247-252`
- `src/esr_pace/pace_calc.py:317`

---

## 🟡 MEDIUM Priority Issues

### #4: Setup Logging Code Duplication
**Status**: Open
**Priority**: MEDIUM
**Category**: Code Quality - DRY Violation

**Description**:
The same `setup_logging()` function is duplicated across 3 entry point scripts.

**Locations**:
- `main.py:35-50`
- `batch_etl.py:32-47`
- `fetch_historical_data.py:38-49`

**Recommended Fix**:
Create shared logging configuration:
```python
# Add to src/esr_pace/config.py
def setup_logging(verbose: bool = False, log_file: str = 'esr_etl.log') -> None:
    """Setup logging configuration."""
    # Move implementation here
```

---

### #5: Large Module - pace_calc.py
**Status**: Open
**Priority**: MEDIUM
**Category**: Code Organization

**Description**:
The `pace_calc.py` module contains 1,389 lines with multiple responsibilities:
- PaceAnalyzer class (main analysis engine)
- Dataclasses (PaceMetrics, StatisticalSummary)
- Visualization creation (multiple chart types)
- Report generation
- Recommendation engine

**Recommended Fix**:
Break into focused modules:
```
src/esr_pace/
├── pace_calc.py         # Core analysis logic (~400 lines)
├── pace_viz.py          # Visualization functions (~400 lines)
├── pace_reports.py      # Report generation (~300 lines)
└── pace_models.py       # Dataclasses and models (~100 lines)
```

---

### #6: `SELECT *` Queries
**Status**: Open
**Priority**: MEDIUM
**Category**: Performance

**Description**:
Using `SELECT *` is inefficient and prevents index-only scans.

**Locations**:
- `src/esr_pace/data_store.py:290`
- `src/esr_pace/data_store.py:324`

**Recommended Fix**:
Specify needed columns explicitly:
```sql
SELECT commodity_code, market_year, week_ending,
       weekly_exports_mt, accumulated_exports_mt,
       outstanding_sales_mt, total_commitment_mt
FROM fact_esr_world_weekly
WHERE ...
```

---

### #7: Missing Database Composite Index
**Status**: Open
**Priority**: MEDIUM
**Category**: Performance

**Description**:
No composite index on `(commodity_code, market_year, week_ending)` for primary queries.

**Recommended Fix**:
```sql
CREATE INDEX IF NOT EXISTS idx_esr_full_key
ON fact_esr_world_weekly(commodity_code, market_year, week_ending);
```

**File to Modify**:
- `src/esr_pace/data_store.py:76-89` (add to _ensure_schema method)

---

### #8: Broad Exception Handlers
**Status**: Open
**Priority**: MEDIUM
**Category**: Error Handling

**Description**:
Several locations use broad `except Exception as e:` which can mask unexpected errors.

**Locations**:
- `src/esr_pace/etl.py:110-112`
- `src/esr_pace/data_store.py:267-270`
- Multiple other locations

**Recommended Fix**:
Use specific exception types:
```python
# Instead of:
except Exception as e:
    # handle

# Use:
except (requests.RequestException, ValueError, sqlite3.Error) as e:
    # handle
```

---

### #9: Export Projection Methodology (Deferred)
**Status**: On Backburner (Simplified 2025-12-08)
**Priority**: MEDIUM
**Category**: Analysis Enhancement

**Current Approach (Simplified)**:
Dashboard now uses a clean, simple approach:
- Shows dotted line from current exports → USDA target at Week 53
- References official USDA estimate as the target (24.49M MT)
- Focuses on pace vs. target rather than complex forecasting

**Implementation** (enhanced_wheat_comparison.py:314-335):
```python
# Simple projection line from current week to Week 53 at USDA target
fig.add_trace(
    go.Scatter(
        x=[current_weeks, 53],
        y=[current_total, estimate_mt],
        mode='lines',
        name=f'Path to USDA Target ({estimate_mt:.1f}M MT)',
        line=dict(color=BENDIGO_COLORS['primary'], width=1.5, dash='dot')
    )
)
```

**Future Enhancement Options** (if needed):
When projection modeling becomes priority, consider:

**Option 1: Momentum-Adjusted Projection**
- Calculate current deviation from 5-year average (e.g., +31.5%)
- Apply regression-to-mean factor (60-70%)
- Project: historical_avg_final × (1 + current_deviation × persistence_factor)

**Option 2: Commitments-Based Projection**
- Outstanding sales conversion (75% typical)
- New sales needed to hit target × shipment rate (60%)
- Floor: Don't project below committed volume

**Option 3: Two-Scenario Display**
- Conservative: Commitments-based floor
- Optimistic: Momentum-adjusted ceiling
- Gives stakeholders range instead of point estimate

**Decision Rationale**:
- Chart was getting too busy with multiple projection lines
- USDA estimate is authoritative and sufficient for now
- Complex projection modeling on backburner until stakeholder need arises
- Current approach is clean, professional, and meets immediate requirements

**Priority Justification**:
MEDIUM because:
- Current simple approach works well
- Enhancement would add analytical value but not urgent
- Can revisit when stakeholder feedback indicates need

---

### #10: Missing Type Hints
**Status**: Open
**Priority**: MEDIUM
**Category**: Code Quality

**Description**:
`enhanced_wheat_comparison.py` lacks type hints, inconsistent with architecture guidelines.

**Functions Needing Type Hints**:
- `get_all_wheat_data()` - missing return type
- `calculate_historical_stats()` - missing parameter and return types
- `load_usda_estimates()` - missing parameter types
- `create_enhanced_comparison_dashboard()` - missing return type

**Recommended Fix**:
```python
from typing import Tuple, Dict, List

def get_all_wheat_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Get comprehensive wheat data including historical context."""
    ...

def calculate_historical_stats(
    all_wheat_historical: pd.DataFrame,
    years_for_avg: List[int] = [2020, 2021, 2022, 2023, 2024]
) -> Dict[int, Dict[str, float]]:
    """Calculate 5-year average and range for All Wheat exports."""
    ...
```

---

### #10: Output Files in Git
**Status**: Open
**Priority**: MEDIUM
**Category**: Version Control

**Description**:
Generated HTML output files are tracked in git, increasing repository size.

**Recommended Fix**:
```bash
# Ensure .gitignore contains:
output/*.html
output/**/*.html
*.log

# Remove from git:
git rm --cached output/*.html
```

---

### #11: Inconsistent Baseline Documentation
**Status**: Open
**Priority**: MEDIUM
**Category**: Documentation

**Description**:
Mixed references to "3-year" and "5-year" baselines across documentation.

**Locations**:
- `docs/PROJECT_SUMMARY.md:29` - says "3-year"
- `docs/data_dictionary.md:60` - references "3-year"
- Code correctly uses 5-year baseline

**Recommended Fix**:
Update all documentation to consistently reference "5-year historical baseline (upgraded from 3-year in 2024)".

---

## 🟢 LOW Priority Issues

### #12: Bendigo Colors Code Duplication
**Status**: Open
**Priority**: LOW
**Category**: Code Quality

**Description**:
The same `BENDIGO_COLORS` dictionary is defined in 2 files:
- `enhanced_wheat_comparison.py:21-33`
- `src/esr_pace/pace_calc.py:17-30`

**Recommended Fix**:
Create `src/esr_pace/theme.py` with centralized color definitions.

---

### #13: Misplaced Script File
**Status**: Open
**Priority**: LOW
**Category**: File Organization

**Description**:
A 13-line test script exists in `/scripts/test.py` but this directory pattern is not documented.

**Recommended Fix**:
Either remove if no longer needed or document the `/scripts/` directory purpose.

---

### #14: Commented Import - scipy.stats
**Status**: Open
**Priority**: LOW
**Category**: Code Cleanliness

**Description**:
Commented-out import suggests dead code in `pace_calc.py:11`:
```python
# from scipy import stats
```

**Recommended Fix**:
Either remove entirely or document why approximation is used instead of scipy.

---

### #15: Magic Numbers Without Constants
**Status**: Open
**Priority**: LOW
**Category**: Code Readability

**Description**:
Magic numbers used without named constants in `pace_calc.py:354, 426`.

**Recommended Fix**:
```python
CONFIDENCE_INTERVAL_Z_SCORE = 2.0  # 95% confidence interval
OUTLIER_Z_SCORE_THRESHOLD = 2.0    # 2 standard deviations

margin_of_error = CONFIDENCE_INTERVAL_Z_SCORE * (accumulated_std / np.sqrt(n_years))
```

---

### #16: Long Function - create_enhanced_comparison_dashboard
**Status**: Open
**Priority**: LOW
**Category**: Code Organization

**Description**:
The main dashboard function in `enhanced_wheat_comparison.py:163-804` is 642 lines long.

**Recommended Fix**:
Break into smaller functions:
```python
def create_enhanced_comparison_dashboard():
    data = prepare_data()
    fig = create_subplot_layout()
    add_pace_chart(fig, data)
    add_pipeline_chart(fig, data)
    add_class_comparison(fig, data)
    add_annotations(fig, data)
    return save_dashboard(fig)
```

---

## 📊 Issue Summary

| Severity | Count | % of Total |
|----------|-------|-----------|
| CRITICAL | 0 | 0% |
| HIGH | 3 | 17.6% |
| MEDIUM | 9 | 52.9% |
| LOW | 5 | 29.4% |
| **Total** | **17** | **100%** |

---

## 🎯 Recommended Next Steps

### Sprint 1 (Next 1-2 weeks)
1. ✅ HIGH #1: Centralize commodity mappings
2. ✅ HIGH #3: Replace .iterrows() with vectorized operations
3. ⚙️ MEDIUM #7: Add composite database index

### Sprint 2 (2-4 weeks)
4. ⚙️ HIGH #2: Refactor SQLite connection management (careful testing required)
5. ⚙️ MEDIUM #4: Centralize setup logging
6. ⚙️ MEDIUM #9: Add type hints to enhanced_wheat_comparison.py

### Future Enhancements
7. 🔄 MEDIUM #5: Split pace_calc.py into focused modules
8. 🔄 MEDIUM #6: Replace SELECT * queries
9. 🔄 MEDIUM #8: Make exception handlers more specific

---

## 📝 Notes

- All CRITICAL issues have been resolved
- 5 HIGH priority issues resolved, 3 deferred for careful refactoring
- MEDIUM/LOW issues are tracked for future sprints
- No issues block production deployment
- Focus on HIGH priority items first to reduce technical debt

**Maintainer**: Update this file when issues are resolved or new issues are discovered.
