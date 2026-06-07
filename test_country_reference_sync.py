"""Country reference sync lives in the pipeline, age-gated via metadata."""
import pandas as pd

from src.esr_pace.data_store import ESRDataStore
from src.esr_pace.etl import ESRETLPipeline


def _pipe(tmp_path, monkeypatch, calls):
    store = ESRDataStore(db_path=str(tmp_path / "test.db"))
    pipe = ESRETLPipeline(data_store=store, api_key="test-key")
    monkeypatch.setattr(
        pipe.api_client, 'get_countries',
        lambda: calls.append(1) or [
            {'countryCode': 1220, 'countryName': 'CANADA',
             'countryDescription': 'CANADA', 'regionId': 1,
             'gencCode': 'CAN'}])
    return pipe


def test_sync_populates_dim_country_and_sets_metadata(tmp_path, monkeypatch):
    calls = []
    pipe = _pipe(tmp_path, monkeypatch, calls)
    pipe.ensure_country_reference()
    assert calls == [1]
    row = pipe.data_store._get_connection().execute(
        "SELECT country_name FROM dim_country WHERE country_code=1220").fetchone()
    assert row == ('CANADA',)
    assert pipe.data_store.get_metadata('country_reference_synced_at') is not None


def test_sync_runs_once_per_pipeline_instance(tmp_path, monkeypatch):
    calls = []
    pipe = _pipe(tmp_path, monkeypatch, calls)
    pipe.ensure_country_reference()
    pipe.ensure_country_reference()
    assert calls == [1]


def test_fresh_metadata_skips_refetch_across_instances(tmp_path, monkeypatch):
    calls = []
    pipe = _pipe(tmp_path, monkeypatch, calls)
    pipe.ensure_country_reference()
    # New pipeline on the same DB within the age window → no refetch.
    pipe2 = _pipe(tmp_path, monkeypatch, calls)
    pipe2.ensure_country_reference()
    assert calls == [1]


def test_run_etl_triggers_sync(tmp_path, monkeypatch):
    """The backfill path (direct run_etl) must populate dim_country too."""
    calls = []
    pipe = _pipe(tmp_path, monkeypatch, calls)
    monkeypatch.setattr(
        pipe.api_client, 'get_release_info_for_commodity',
        lambda code: {'releaseTimeStamp': '2026-01-01T00:00:00',
                      'marketYear': 2026})
    monkeypatch.setattr(
        pipe, 'extract_raw_data', lambda code, my: pd.DataFrame({'x': [1]}))
    monkeypatch.setattr(
        pipe, 'transform_to_world_aggregates',
        lambda raw, code, my: pd.DataFrame({'x': [1]}))
    monkeypatch.setattr(pipe, 'load_to_database', lambda df: 1)
    monkeypatch.setattr(
        pipe, 'transform_to_country_weekly',
        lambda raw, code, my: pd.DataFrame())
    res = pipe.run_etl(401, force_refresh=True, validate_data=False)
    assert res['success'] is True
    assert calls == [1]
