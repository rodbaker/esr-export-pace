"""Tests for the grains dashboard's MY derivation and week alignment."""
import sqlite3

import pandas as pd

from enhanced_grains_comparison import load_world_history, pace_metric


def _mem_db(rows):
    conn = sqlite3.connect(':memory:')
    conn.execute("""
        CREATE TABLE fact_esr_world_weekly (
            commodity_code INT, market_year INT, week_ending TEXT,
            weekly_exports_mt REAL, accumulated_exports_mt REAL,
            outstanding_sales_mt REAL, total_commitment_mt REAL)
    """)
    conn.executemany(
        "INSERT INTO fact_esr_world_weekly VALUES (?,?,?,?,?,?,?)", rows)
    return conn


def test_load_world_history_ordinal_mw():
    # Ordinal alignment: week index = position within the season,
    # immune to which weekday the MY start lands on. MY2025's first
    # reported week ends 2024-06-13 — calendar marketing-week would call
    # that week 2; ordinal alignment calls it week 1.
    conn = _mem_db([
        (107, 2026, '2025-06-05', 1, 100, 1, 200),
        (107, 2026, '2025-06-12', 1, 200, 1, 300),
        (107, 2025, '2024-06-13', 1, 110, 1, 210),
    ])
    df = load_world_history(conn, 107)
    assert list(df[df['market_year'] == 2026]['mw']) == [1, 2]
    assert list(df[df['market_year'] == 2025]['mw']) == [1]


def test_pace_metric_uses_passed_current_my():
    # 2025 is "current" here even though later years could exist elsewhere —
    # the metric must use the passed-in MY, not a module-level constant.
    hist = pd.DataFrame({
        'market_year': [2024, 2025],
        'week_ending': pd.to_datetime(['2023-06-08', '2024-06-06']),
        'mw': [1, 1],
        'accumulated_exports_mt': [100.0, 130.0],
        'total_commitment_mt': [200.0, 260.0],
    })
    m = pace_metric(hist, 2025)
    assert m['current_mt'] == 130.0
    assert m['avg_mt'] == 100.0
    assert round(m['pace_pct'], 1) == 30.0


def test_pace_metric_no_baseline_is_none_not_zero():
    hist = pd.DataFrame({
        'market_year': [2026],
        'week_ending': pd.to_datetime(['2025-09-04']),
        'mw': [1],
        'accumulated_exports_mt': [100.0],
        'total_commitment_mt': [150.0],
    })
    m = pace_metric(hist, 2026)
    assert m['pace_pct'] is None   # was 0.0 — read as "on par with history"
