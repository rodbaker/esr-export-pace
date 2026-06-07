#!/usr/bin/env python3
"""
export_reporting_snapshot.py
Exports the latest ESR row for each enabled wheat commodity with
5-year baseline deviations to output/us_wheat_export_pace_latest.csv.

Does not call the USDA API. Reads from data/esr_data.db.
Baseline SQL uses explicit parentheses to avoid the SQLite operator-
precedence bug present in the v_current_marketing_year view.
"""

import csv
import sqlite3
import sys
import yaml
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from esr_pace.marketing_week import marketing_week  # noqa: E402

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "esr_data.db"
OUTPUT_PATH = PROJECT_DIR / "output" / "us_wheat_export_pace_latest.csv"
COMMODITIES_PATH = PROJECT_DIR / "config" / "commodities.yaml"

FIELDNAMES = [
    "commodity_code",
    "commodity_name",
    "market_year",
    "week_ending",
    "marketing_week",
    "weekly_exports_mt",
    "accumulated_exports_mt",
    "outstanding_sales_mt",
    "total_commitment_mt",
    "baseline_accumulated_mt",
    "pace_deviation_mt",
    "pace_deviation_pct",
]

BASELINE_YEARS = 5
BASELINE_MIN_YEARS = 2

# This snapshot is wheat-only by design (file name + June-1 hardcoded baseline
# SQL). Other commodities (corn/soy complex) belong in a separate snapshot.
WHEAT_CODES = {101, 102, 103, 104, 105, 106, 107, 201}


def load_commodities(path: Path) -> list[dict]:
    """Return enabled wheat commodity dicts from commodities.yaml.

    The non-wheat commodities (corn, soybeans, soy meal, soy oil) are
    intentionally excluded here — this snapshot is wheat-specific and the
    baseline SQL below hardcodes the June-1 marketing year start.
    """
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return [
        c for c in cfg["commodities"]
        if c.get("enabled", False) and c["code"] in WHEAT_CODES
    ]


def fetch_latest_rows(db_path: Path, codes: list[int]) -> dict[int, dict]:
    """Latest row per commodity from the current marketing year."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    result: dict[int, dict] = {}
    try:
        for code in codes:
            row = conn.execute(
                """
                SELECT commodity_code, market_year, week_ending,
                       weekly_exports_mt, accumulated_exports_mt,
                       outstanding_sales_mt, total_commitment_mt
                FROM fact_esr_world_weekly
                WHERE commodity_code = ?
                  AND market_year = (
                        SELECT MAX(market_year)
                        FROM fact_esr_world_weekly
                        WHERE commodity_code = ?
                  )
                ORDER BY week_ending DESC
                LIMIT 1
                """,
                (code, code),
            ).fetchone()
            if row:
                result[code] = dict(row)
    finally:
        conn.close()
    return result


def fetch_baseline_accumulated(db_path: Path, commodity_code: int, mw: int) -> float | None:
    """
    N-year average accumulated exports at marketing_week mw.
    Uses the corrected SQL formula (explicit inner parentheses).
    Returns None if fewer than BASELINE_MIN_YEARS of matching data.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        bounds = conn.execute(
            "SELECT MAX(market_year), MIN(market_year) FROM fact_esr_world_weekly WHERE commodity_code = ?",
            (commodity_code,),
        ).fetchone()
        if not bounds or bounds[0] is None:
            return None
        max_year, min_year = bounds
        end_year = max_year  # exclusive: baseline = years before current
        start_year = max(min_year, end_year - BASELINE_YEARS)
        if (end_year - start_year) < BASELINE_MIN_YEARS:
            return None

        avg, n = conn.execute(
            """
            SELECT AVG(accumulated_exports_mt), COUNT(*)
            FROM fact_esr_world_weekly
            WHERE commodity_code = ?
              AND market_year >= ? AND market_year < ?
              AND CAST(
                    (julianday(week_ending) - julianday((market_year - 1) || '-06-01'))
                    / 7.0 + 1 AS INTEGER
                  ) = ?
            """,
            (commodity_code, start_year, end_year, mw),
        ).fetchone()

        if avg is None or n < BASELINE_MIN_YEARS:
            return None
        return round(avg, 2)
    finally:
        conn.close()


def build_rows(commodities: list[dict], latest: dict[int, dict], db_path: Path) -> list[dict]:
    """Assemble output rows with baseline enrichment where available."""
    rows = []
    for commodity in commodities:
        code = commodity["code"]
        raw = latest.get(code)
        if raw is None:
            continue

        mw = marketing_week(raw["market_year"], date.fromisoformat(raw["week_ending"]))

        row: dict = {
            "commodity_code": code,
            "commodity_name": commodity["name"],
            "market_year": raw["market_year"],
            "week_ending": raw["week_ending"],
            "marketing_week": mw,
            "weekly_exports_mt": raw["weekly_exports_mt"],
            "accumulated_exports_mt": raw["accumulated_exports_mt"],
            "outstanding_sales_mt": raw["outstanding_sales_mt"],
            "total_commitment_mt": raw["total_commitment_mt"],
            "baseline_accumulated_mt": "",
            "pace_deviation_mt": "",
            "pace_deviation_pct": "",
        }

        baseline = fetch_baseline_accumulated(db_path, code, mw)
        if baseline is not None:
            acc = raw["accumulated_exports_mt"]
            dev = round(acc - baseline, 2)
            dev_pct = round((dev / baseline) * 100, 2) if baseline else ""
            row["baseline_accumulated_mt"] = baseline
            row["pace_deviation_mt"] = dev
            row["pace_deviation_pct"] = dev_pct

        rows.append(row)
    return rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    commodities = load_commodities(COMMODITIES_PATH)
    codes = [c["code"] for c in commodities]
    latest = fetch_latest_rows(DB_PATH, codes)
    rows = build_rows(commodities, latest, DB_PATH)
    write_csv(rows, OUTPUT_PATH)

    print(f"Written {len(rows)} rows → {OUTPUT_PATH}")
    for row in rows:
        dev_pct = row["pace_deviation_pct"]
        pace_str = f"  {dev_pct:+.1f}% vs {BASELINE_YEARS}yr avg" if dev_pct != "" else "  (no baseline)"
        acc_mt = row["accumulated_exports_mt"]
        print(f"  {row['commodity_name']:20} MW{row['marketing_week']:>2}  {acc_mt / 1e6:.3f}Mt acc{pace_str}")


if __name__ == "__main__":
    main()
