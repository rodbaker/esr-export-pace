"""
Tests for marketing_week helper and export_reporting_snapshot.py.
Run with: python3 -m unittest discover (from esr_export_pace project root)
Does not call the USDA API.
"""

import csv
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from esr_pace.marketing_week import marketing_week  # noqa: E402

import export_reporting_snapshot as snap  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal DB helper
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE fact_esr_world_weekly (
    commodity_code INTEGER NOT NULL,
    market_year INTEGER NOT NULL,
    week_ending DATE NOT NULL,
    weekly_exports_mt REAL NOT NULL DEFAULT 0,
    accumulated_exports_mt REAL NOT NULL DEFAULT 0,
    outstanding_sales_mt REAL NOT NULL DEFAULT 0,
    net_sales_mt REAL DEFAULT 0,
    total_commitment_mt REAL NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (commodity_code, market_year, week_ending)
)
"""


def _make_db(path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(_SCHEMA)
    conn.executemany(
        "INSERT INTO fact_esr_world_weekly "
        "(commodity_code, market_year, week_ending, weekly_exports_mt, "
        "accumulated_exports_mt, outstanding_sales_mt, total_commitment_mt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# marketing_week unit tests
# ---------------------------------------------------------------------------

class TestMarketingWeek(unittest.TestCase):
    def test_week_1_when_june_1_is_thursday(self):
        # June 1, 2017 is Thursday → first week-ending = June 1
        self.assertEqual(marketing_week(2018, date(2017, 6, 1)), 1)

    def test_week_1_when_june_1_is_sunday(self):
        # June 1, 2025 is Sunday → first Thursday = June 5 (MY2026)
        self.assertEqual(marketing_week(2026, date(2025, 6, 5)), 1)

    def test_week_2(self):
        self.assertEqual(marketing_week(2026, date(2025, 6, 12)), 2)

    def test_week_22_matches_oct_30_2025(self):
        # 21 full weeks after June 5, 2025 = Oct 30, 2025
        self.assertEqual(marketing_week(2026, date(2025, 10, 30)), 22)

    def test_week_1_when_june_1_is_wednesday(self):
        # June 1, 2016 is Wednesday → first Thursday = June 2 (MY2017)
        self.assertEqual(marketing_week(2017, date(2016, 6, 2)), 1)

    def test_week_2_when_june_1_is_wednesday(self):
        self.assertEqual(marketing_week(2017, date(2016, 6, 9)), 2)

    def test_result_is_positive_integer(self):
        for d in (date(2025, 6, 5), date(2025, 9, 18), date(2026, 5, 28)):
            result = marketing_week(2026, d)
            self.assertIsInstance(result, int)
            self.assertGreater(result, 0)
            self.assertLessEqual(result, 54)


# ---------------------------------------------------------------------------
# fetch_latest_rows
# ---------------------------------------------------------------------------

class TestFetchLatestRows(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        _make_db(self.db, [
            (107, 2026, "2025-06-05", 115709.0, 115709.0, 5793976.0, 5909685.0),
            (107, 2026, "2025-06-12", 363538.0, 479247.0, 5857608.0, 6336855.0),
            (101, 2026, "2025-06-05",  50000.0,  50000.0, 2000000.0, 2050000.0),
        ])

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_latest_week_per_commodity(self):
        result = snap.fetch_latest_rows(self.db, [107, 101])
        self.assertEqual(result[107]["week_ending"], "2025-06-12")
        self.assertEqual(result[101]["week_ending"], "2025-06-05")

    def test_missing_commodity_absent_from_result(self):
        result = snap.fetch_latest_rows(self.db, [999])
        self.assertNotIn(999, result)


# ---------------------------------------------------------------------------
# build_rows
# ---------------------------------------------------------------------------

class TestBuildRows(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        _make_db(self.db, [
            (107, 2026, "2025-06-05", 115709.0, 115709.0, 5793976.0, 5909685.0),
        ])
        self.commodities = [
            {"code": 107, "name": "All Wheat"},
            {"code": 101, "name": "Wheat - HRW"},  # no data in DB
        ]
        self.latest = snap.fetch_latest_rows(self.db, [107, 101])

    def tearDown(self):
        self._tmp.cleanup()

    def test_only_commodities_with_data_appear(self):
        rows = snap.build_rows(self.commodities, self.latest, self.db)
        codes = [r["commodity_code"] for r in rows]
        self.assertIn(107, codes)
        self.assertNotIn(101, codes)

    def test_marketing_week_column_is_correct(self):
        rows = snap.build_rows(self.commodities, self.latest, self.db)
        row = next(r for r in rows if r["commodity_code"] == 107)
        # MY2026, June 1 2025 = Sunday → week 1 ends June 5
        self.assertEqual(row["marketing_week"], 1)

    def test_commodity_name_populated(self):
        rows = snap.build_rows(self.commodities, self.latest, self.db)
        row = next(r for r in rows if r["commodity_code"] == 107)
        self.assertEqual(row["commodity_name"], "All Wheat")

    def test_baseline_empty_without_history(self):
        rows = snap.build_rows(self.commodities, self.latest, self.db)
        row = next(r for r in rows if r["commodity_code"] == 107)
        self.assertEqual(row["baseline_accumulated_mt"], "")
        self.assertEqual(row["pace_deviation_mt"], "")
        self.assertEqual(row["pace_deviation_pct"], "")


# ---------------------------------------------------------------------------
# fetch_baseline_accumulated
# ---------------------------------------------------------------------------

# Week-1 Thursday dates by marketing year (first Thursday >= June 1):
#   MY2021: June 1, 2020 = Monday  → June  4, 2020
#   MY2022: June 1, 2021 = Tuesday → June  3, 2021
#   MY2023: June 1, 2022 = Wednesday → June 2, 2022
#   MY2024: June 1, 2023 = Thursday  → June 1, 2023
#   MY2025: June 1, 2024 = Saturday  → June 6, 2024
#   MY2026: June 1, 2025 = Sunday    → June 5, 2025

_BASELINE_ROWS = [
    (107, 2021, "2020-06-04", 100000.0, 100000.0, 1000000.0, 1100000.0),
    (107, 2022, "2021-06-03", 110000.0, 110000.0, 1100000.0, 1210000.0),
    (107, 2023, "2022-06-02", 120000.0, 120000.0, 1200000.0, 1320000.0),
    (107, 2024, "2023-06-01", 130000.0, 130000.0, 1300000.0, 1430000.0),
    (107, 2025, "2024-06-06", 140000.0, 140000.0, 1400000.0, 1540000.0),
    (107, 2026, "2025-06-05", 150000.0, 150000.0, 1500000.0, 1650000.0),
]


class TestFetchBaselineAccumulated(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        _make_db(self.db, _BASELINE_ROWS)

    def tearDown(self):
        self._tmp.cleanup()

    def test_baseline_is_five_year_average(self):
        # Current = MY2026; baseline = MY2021-2025: avg(100k,110k,120k,130k,140k) = 120k
        result = snap.fetch_baseline_accumulated(self.db, 107, 1)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 120000.0, places=0)

    def test_returns_none_when_only_current_year(self):
        with tempfile.TemporaryDirectory() as d:
            db2 = Path(d) / "tiny.db"
            _make_db(db2, [
                (107, 2026, "2025-06-05", 150000.0, 150000.0, 1500000.0, 1650000.0),
            ])
            self.assertIsNone(snap.fetch_baseline_accumulated(db2, 107, 1))

    def test_returns_none_for_unknown_commodity(self):
        self.assertIsNone(snap.fetch_baseline_accumulated(self.db, 999, 1))


# ---------------------------------------------------------------------------
# CSV shape (end-to-end write_csv)
# ---------------------------------------------------------------------------

class TestCsvShape(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        db = self.tmp / "test.db"
        _make_db(db, [
            (107, 2026, "2025-06-05", 115709.0, 115709.0, 5793976.0, 5909685.0),
            (101, 2026, "2025-06-05",  50000.0,  50000.0, 2000000.0, 2050000.0),
        ])
        commodities = [
            {"code": 107, "name": "All Wheat"},
            {"code": 101, "name": "Wheat - HRW"},
        ]
        latest = snap.fetch_latest_rows(db, [107, 101])
        rows = snap.build_rows(commodities, latest, db)
        self.output = self.tmp / "out.csv"
        snap.write_csv(rows, self.output)

    def tearDown(self):
        self._tmp.cleanup()

    def test_csv_file_created(self):
        self.assertTrue(self.output.exists())

    def test_csv_has_all_expected_columns(self):
        with open(self.output) as f:
            headers = csv.DictReader(f).fieldnames
        self.assertEqual(headers, snap.FIELDNAMES)

    def test_csv_row_count_matches_input_commodities(self):
        with open(self.output) as f:
            self.assertEqual(len(list(csv.DictReader(f))), 2)

    def test_marketing_week_is_valid_integer(self):
        with open(self.output) as f:
            for row in csv.DictReader(f):
                mw = int(row["marketing_week"])
                self.assertGreater(mw, 0)
                self.assertLessEqual(mw, 54)

    def test_baseline_fields_empty_without_history(self):
        with open(self.output) as f:
            for row in csv.DictReader(f):
                self.assertEqual(row["baseline_accumulated_mt"], "")
                self.assertEqual(row["pace_deviation_mt"], "")
                self.assertEqual(row["pace_deviation_pct"], "")


if __name__ == "__main__":
    unittest.main()
