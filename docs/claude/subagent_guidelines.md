# Claude Subagent Guidelines - ESR Project

## Subagent Induction Process

When bringing specialist subagents onto this project, follow this systematic onboarding approach to ensure they have full context and can contribute effectively.

### Standard Induction Checklist

#### 1. Project Context Reading
**Required Files** (in order):
- `docs/PROJECT_SUMMARY.md` - Overall system architecture and status
- `docs/USDA ESR Query INFORMATION.md` - API and data source details
- `docs/data_dictionary.md` - Field definitions and business logic
- `docs/schema.sql` - Database structure and relationships
- `docs/validation_checks.md` - Data quality requirements
- `docs/claude/development_log.md` - Technical challenges and solutions

#### 2. Code Architecture Review
**Core Files to Understand**:
- `src/esr_pace/api_client.py` - API integration patterns
- `src/esr_pace/data_store.py` - Database operations and data cleaning
- `src/esr_pace/etl.py` - Pipeline orchestration
- `src/esr_pace/pace_calc.py` - Statistical analysis engine
- `main.py` - CLI interface and integration

#### 3. Business Context
**Key Concepts to Convey**:
- **Marketing Years**: June 1 - May 31 agricultural cycles
- **Export Pace Analysis**: Performance vs 3-year historical averages
- **World Aggregation**: Country-level data rolled up to totals
- **Deviation Severity**: Statistical classification (normal/significant/major/critical)
- **Volatility Scoring**: Measure of week-to-week consistency

### Subagent Type Guidelines

#### General-Purpose Agent
**Best Used For**:
- Multi-step algorithmic development (e.g., pace calculations)
- Complex data analysis requiring multiple tool calls
- Research tasks requiring file searches and code review
- Integration work spanning multiple components

**Induction Approach**:
```
You are working on the ESR Export Pace Analysis project. Before starting your specific task, please:

1. Read docs/PROJECT_SUMMARY.md to understand the overall system
2. Review docs/claude/development_log.md for technical context and previous solutions
3. Examine the relevant source files in src/esr_pace/ for implementation patterns
4. Your specific task: [detailed task description]

Key technical patterns to follow:
- Use query parameters (not headers) for USDA API authentication
- Clean data types before SQLite operations using _clean_data_for_sqlite() pattern
- Convert numpy types to Python natives for database binding
- Use layout dictionary approach for Plotly chart modifications

Business context:
- Marketing years run June 1 - May 31
- Pace analysis compares current exports vs 3-year averages
- Deviation severity: normal (<10%), significant (10-25%), major (25-50%), critical (>50%)
```

#### Python-Dev Subagent
**Best Used For**:
- Pure algorithm implementation
- Data structure optimization
- Code refactoring and cleanup
- Bug fixing in specific functions

**Induction Approach**:
```
You are the Python specialist on the ESR Export Pace Analysis project. 

Context: This is an agricultural export data pipeline that processes USDA ESR data and performs statistical pace analysis against historical baselines.

Key technical constraints you must follow:
- SQLite compatibility requires cleaning NaN/infinity values and converting numpy types
- USDA ESR API uses query parameter authentication (api_key=value)
- Marketing week calculations use Julian date arithmetic with June 1 year boundaries
- Plotly visualizations should use layout dictionary syntax for compatibility

Before implementing your specific task, review:
- src/esr_pace/[relevant_file].py for existing patterns
- The current data flow and error handling approaches

Your specific task: [detailed task description]
```

#### SQL/ETL Specialist
**Best Used For**:
- Database schema optimization
- Complex SQL query development  
- ETL pipeline performance improvements
- Data validation rule implementation

**Induction Approach**:
```
You are the SQL/ETL specialist for the ESR Export Pace Analysis project.

Database Context:
- SQLite backend with agricultural export fact tables
- Marketing year partitioning (June 1 - May 31 cycles)
- World aggregation from country-level data
- 3-year historical baseline calculations for pace analysis

Key technical requirements:
- Handle mixed data types and null values in pandas DataFrames
- Marketing week calculation: (julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1
- Parameter binding requires Python native types, not numpy
- World aggregation uses country_code = 'WO' or explicit SUM() operations

Review docs/schema.sql and src/esr_pace/data_store.py before starting.

Your specific task: [detailed task description]
```

### Success Patterns

#### Effective Subagent Usage
✅ **Do**:
- Provide comprehensive business context upfront
- Reference specific files and line numbers for code patterns
- Include known technical gotchas and solutions
- Set clear boundaries for the subagent's scope
- Ask subagent to confirm understanding before proceeding

❌ **Don't**:
- Assume subagents know project-specific business logic
- Skip technical constraint explanations
- Provide task instructions without architecture context
- Use subagents for trivial single-step tasks

#### Example Successful Subagent Task
**Scenario**: Implementing new commodity support
**Induction**: Full project context + schema review + existing commodity patterns
**Task**: Extend ETL pipeline to support commodity code 57 (corn) with same pace analysis
**Result**: Clean implementation following established patterns, no rework needed

#### Example Suboptimal Subagent Task
**Scenario**: Fix marketing week calculation bug  
**Issue**: Task given without context about Julian date requirements or marketing year boundaries
**Result**: Multiple iterations needed to understand agricultural calendar requirements

### Continuous Improvement

#### Metrics to Track
- Subagent task completion rate without rework
- Time to productive contribution after induction  
- Code quality and pattern consistency
- Knowledge retention across similar tasks

#### Feedback Loop
- Document new technical gotchas discovered by subagents
- Update induction templates based on common confusion points
- Maintain shared glossary of project-specific terminology
- Regular review of subagent effectiveness and context gaps