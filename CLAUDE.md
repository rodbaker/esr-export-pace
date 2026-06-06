# CLAUDE.md — ESR Export Pace

## What This Project Does

Tracks US wheat export performance against historical baselines using USDA Export Sales
Reporting (ESR) API data. Covers 7 wheat classes (HRW, SRW, HRS, White, Durum, Soft White,
All Wheat). Outputs CSV data and interactive HTML dashboards showing pace vs 5-year average.

See `README.md` for full feature list and `CHEAT_SHEET.md` for quick command reference.

---

## Who Uses This

A bank analyst supporting **Australian agricultural lending**. The US export pace data is
used as a price driver indicator — strong US exports tighten global supply and support
Australian grain prices; weak US exports signal competitive pressure.

This is market intelligence for farm advisory and lending commentary, not trading.

---

## Downstream Integration

This project feeds the **WA Grain Trade Monitor brief assemblers**:

- Interactive: `/monitor-brief` slash command in `/home/roddyb/projects/claude-notebooklm-research/`
- Headless / source-pack: `/home/roddyb/projects/reporter/` (`esr_structured_glob` in its `config.json`)

The assemblers read CSV output from this project to populate the **US Export Pace** section
of a weekly grains market draft.

### What the assembler reads

Primary file: `output/commodity_107_all_wheat_exports.csv`
Secondary file: `output/commodity_101_hrw_wheat_exports.csv` (HRW)

### Fields the assembler depends on

| Field | Description |
|---|---|
| `week_ending` | Date of the reporting week |
| `accumulated_exports_mt` | Running total exports for the marketing year |
| `outstanding_sales_mt` | Pre-sold but not yet shipped |
| `marketing_week_index` | Week number in the marketing year |

Pace vs 5-year average (% ahead/behind) is calculated by the assembler from the CSV data.

**Do not rename these columns or change the `output/` path without updating the assembler.**

### Running the tool

```bash
# Update All Wheat data
python main.py --commodity-code 107

# Update all wheat classes at once
python batch_etl.py --force-refresh

# Quick current totals
python get_current_exports.py
```

---

## Current State

- Working. CSV outputs exist for 6 wheat classes in `output/`.
- SQLite database at `data/` stores full history.
- HTML dashboard at `output/enhanced_wheat_multi_commodity_comparison.html`.
- Full technical docs in `docs/`.
