"""Country-load failures must be visible, not swallowed."""
import pandas as pd

from src.esr_pace.data_store import ESRDataStore
from src.esr_pace.etl import ESRETLPipeline


def _pipeline(tmp_path, monkeypatch):
    store = ESRDataStore(db_path=str(tmp_path / "test.db"))
    pipe = ESRETLPipeline(data_store=store, api_key="test-key")
    # Stub the network/transform surface so run_etl exercises only the
    # orchestration we are testing.
    monkeypatch.setattr(
        pipe.api_client, 'get_release_info_for_commodity',
        lambda code: {'releaseTimeStamp': '2026-01-01T00:00:00',
                      'marketYear': 2026})
    monkeypatch.setattr(pipe.api_client, 'get_countries', lambda: [])
    monkeypatch.setattr(
        pipe, 'extract_raw_data', lambda code, my: pd.DataFrame({'x': [1]}))
    monkeypatch.setattr(
        pipe, 'transform_to_world_aggregates',
        lambda raw, code, my: pd.DataFrame({'x': [1]}))
    monkeypatch.setattr(pipe, 'load_to_database', lambda df: 1)
    monkeypatch.setattr(
        pipe, 'transform_to_country_weekly',
        lambda raw, code, my: pd.DataFrame({'x': [1]}))
    return pipe


def test_country_load_failure_is_recorded(tmp_path, monkeypatch):
    pipe = _pipeline(tmp_path, monkeypatch)

    def boom(df):
        raise RuntimeError("cast failed")
    monkeypatch.setattr(pipe.data_store, 'upsert_country_data', boom)

    res = pipe.run_etl(401, force_refresh=True, validate_data=False)
    assert res['success'] is True               # world load still succeeded
    assert res['country_records_loaded'] == 0
    assert 'cast failed' in res['country_load_error']   # NEW: visible


def test_country_load_success_has_no_error_key(tmp_path, monkeypatch):
    pipe = _pipeline(tmp_path, monkeypatch)
    monkeypatch.setattr(pipe.data_store, 'upsert_country_data', lambda df: 5)

    res = pipe.run_etl(401, force_refresh=True, validate_data=False)
    assert res['success'] is True
    assert res['country_records_loaded'] == 5
    assert 'country_load_error' not in res
