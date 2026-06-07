"""Country name hygiene and key-cast guards."""
import pandas as pd

from src.esr_pace.data_store import ESRDataStore


def _mk_store(tmp_path):
    return ESRDataStore(db_path=str(tmp_path / "test.db"))


def test_upsert_countries_strips_padded_strings(tmp_path):
    store = _mk_store(tmp_path)
    # Real USDA shape — names arrive space-padded (docs/USDA ESR Query
    # INFORMATION.md shows 'CANADA  ', 'GREENLD ').
    store.upsert_countries([{
        'countryCode': 1220, 'countryName': 'CANADA  ',
        'countryDescription': 'CANADA                         ',
        'regionId': 1, 'gencCode': 'CAN ',
    }])
    row = store._get_connection().execute(
        "SELECT country_name, country_description, genc_code "
        "FROM dim_country WHERE country_code=1220").fetchone()
    assert row == ('CANADA', 'CANADA', 'CAN')


def test_existing_padded_rows_trimmed_on_schema_init(tmp_path):
    db = tmp_path / "test.db"
    store = ESRDataStore(db_path=str(db))
    conn = store._get_connection()
    conn.execute(
        "INSERT INTO dim_country (country_code, country_name, "
        "country_description) VALUES (1, 'CANADA  ', 'CANADA   ')")
    conn.commit()
    store.close()

    store2 = ESRDataStore(db_path=str(db))   # _ensure_schema runs TRIM
    row = store2._get_connection().execute(
        "SELECT country_name, country_description FROM dim_country "
        "WHERE country_code=1").fetchone()
    assert row == ('CANADA', 'CANADA')


def _base_row(**overrides):
    row = dict(commodity_code=401, market_year=2026,
               week_ending='2025-09-04', country_code=1220,
               weekly_exports_mt=1.0, accumulated_exports_mt=1.0,
               outstanding_sales_mt=1.0, net_sales_mt=1.0,
               total_commitment_mt=2.0)
    row.update(overrides)
    return row


def test_upsert_country_data_drops_invalid_keys_not_crash(tmp_path, caplog):
    store = _mk_store(tmp_path)
    df = pd.DataFrame([
        _base_row(),
        _base_row(country_code=None),        # was: astype('int64') crash
        _base_row(market_year='not-a-year', country_code=1230),
    ])
    n = store.upsert_country_data(df)
    assert n == 1                            # the valid row still loads
    stored = store._get_connection().execute(
        "SELECT COUNT(*) FROM fact_esr_country_weekly").fetchone()[0]
    assert stored == 1
    assert any('invalid key' in r.message.lower() for r in caplog.records)


def test_upsert_country_data_all_invalid_returns_zero(tmp_path):
    store = _mk_store(tmp_path)
    df = pd.DataFrame([_base_row(country_code='not-a-code')])
    assert store.upsert_country_data(df) == 0
