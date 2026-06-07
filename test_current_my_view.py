"""Tests for the per-commodity current-MY view and Python week index."""
import sqlite3

import pandas as pd

from src.esr_pace.data_store import ESRDataStore


def _mk_store(tmp_path):
    return ESRDataStore(db_path=str(tmp_path / "test.db"))


def _rows(code, my, weeks):
    # week_ending values must be Thursdays (schema CHECK) and
    # total_commitment_mt >= accumulated_exports_mt (schema CHECK).
    return pd.DataFrame([{
        'commodity_code': code, 'market_year': my, 'week_ending': w,
        'weekly_exports_mt': 100.0, 'accumulated_exports_mt': 100.0,
        'outstanding_sales_mt': 50.0, 'net_sales_mt': 10.0,
        'total_commitment_mt': 150.0,
    } for w in weeks])


def test_view_scopes_max_year_per_commodity(tmp_path):
    store = _mk_store(tmp_path)
    # Wheat has rolled to MY2027; corn is still on MY2026.
    store.upsert_weekly_data(_rows(107, 2027, ['2026-06-04']))
    store.upsert_weekly_data(_rows(401, 2026, ['2025-09-04']))

    corn = store.get_current_marketing_year_data(401)
    assert len(corn) == 1                       # was 0 with the global-MAX view
    assert corn['market_year'].iloc[0] == 2026

    wheat = store.get_current_marketing_year_data(107)
    assert len(wheat) == 1
    assert wheat['market_year'].iloc[0] == 2027


def test_marketing_week_index_correct_per_commodity(tmp_path):
    store = _mk_store(tmp_path)
    store.upsert_weekly_data(_rows(107, 2027, ['2026-06-04']))  # wk 1, June MY
    store.upsert_weekly_data(_rows(401, 2026, ['2025-09-04']))  # wk 1, Sept MY

    wheat = store.get_current_marketing_year_data(107)
    corn = store.get_current_marketing_year_data(401)
    assert wheat['marketing_week_index'].iloc[0] == 1
    assert corn['marketing_week_index'].iloc[0] == 1


def test_unfiltered_fetch_covers_all_commodities(tmp_path):
    store = _mk_store(tmp_path)
    store.upsert_weekly_data(_rows(107, 2027, ['2026-06-04', '2026-06-11']))
    store.upsert_weekly_data(_rows(401, 2026, ['2025-09-04']))

    df = store.get_current_marketing_year_data()
    assert set(df['commodity_code'].unique()) == {107, 401}
    wheat_idx = df[df['commodity_code'] == 107]['marketing_week_index']
    assert list(wheat_idx) == [1, 2]


def test_broken_view_is_replaced_on_existing_db(tmp_path):
    # Simulate a live DB carrying the old broken view, then re-open.
    db = tmp_path / "old.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE fact_esr_world_weekly (
            commodity_code INTEGER NOT NULL, market_year INTEGER NOT NULL,
            week_ending DATE NOT NULL, weekly_exports_mt REAL NOT NULL DEFAULT 0,
            accumulated_exports_mt REAL NOT NULL DEFAULT 0,
            outstanding_sales_mt REAL NOT NULL DEFAULT 0,
            net_sales_mt REAL DEFAULT 0,
            total_commitment_mt REAL NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (commodity_code, market_year, week_ending))
    """)
    conn.execute("""
        CREATE VIEW v_current_marketing_year AS
        SELECT commodity_code, market_year, week_ending,
               (julianday(week_ending) - julianday(market_year - 1 || '-06-01')) / 7 + 1
                   AS marketing_week_index
        FROM fact_esr_world_weekly
        WHERE market_year = (SELECT MAX(market_year) FROM fact_esr_world_weekly)
    """)
    conn.commit()
    conn.close()

    store = ESRDataStore(db_path=str(db))  # _ensure_schema runs here
    cols = [r[1] for r in store._get_connection().execute(
        "PRAGMA table_info(v_current_marketing_year)")]
    assert 'marketing_week_index' not in cols   # broken SQL index gone
