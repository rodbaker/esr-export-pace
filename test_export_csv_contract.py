"""The exported world CSV honors the downstream assembler contract."""
import pandas as pd

from src.esr_pace.data_store import ESRDataStore

CONTRACT_COLUMNS = ['week_ending', 'accumulated_exports_mt',
                    'outstanding_sales_mt', 'marketing_week_index']


def _rows(code, my, weeks):
    return pd.DataFrame([{
        'commodity_code': code, 'market_year': my, 'week_ending': w,
        'weekly_exports_mt': 100.0, 'accumulated_exports_mt': 100.0,
        'outstanding_sales_mt': 50.0, 'net_sales_mt': 10.0,
        'total_commitment_mt': 150.0,
    } for w in weeks])


def test_export_to_csv_contract_columns_and_correct_index(tmp_path):
    store = ESRDataStore(db_path=str(tmp_path / "test.db"))
    # Two consecutive corn weeks (Sept MY): Thursdays 2025-09-04, 2025-09-11.
    store.upsert_weekly_data(_rows(401, 2026, ['2025-09-04', '2025-09-11']))

    out = tmp_path / "output" / "commodity_401_corn_exports.csv"
    store.export_to_csv(401, str(out))

    df = pd.read_csv(out)
    for col in CONTRACT_COLUMNS:
        assert col in df.columns, f"contract column {col} missing"
    # Sept-start MY → these are weeks 1 and 2 (June-based SQL gave 14/15
    # — and the broken view gave ~351259).
    assert list(df['marketing_week_index']) == [1, 2]


def test_batch_etl_has_no_forked_exporter():
    import batch_etl
    assert not hasattr(batch_etl, 'export_world_csv_with_marketing_week')
