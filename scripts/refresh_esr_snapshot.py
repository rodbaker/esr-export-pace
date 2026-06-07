#!/usr/bin/env python3
"""
refresh_esr_snapshot.py
Two-step pipeline:
  1. batch_etl.py --force-refresh  → pulls USDA API data into esr_data.db
  2. export_reporting_snapshot.py  → writes output/us_wheat_export_pace_latest.csv

ESR_API_KEY must be set via env var or .env file at the project root.
Fails loudly and exits non-zero if the key is missing or either step errors.

Usage (from esr_export_pace/):
  python scripts/refresh_esr_snapshot.py
  ESR_API_KEY=<key> python scripts/refresh_esr_snapshot.py
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "data" / "esr_data.db"


def check_api_key() -> None:
    """Exit early if no key is available (env var takes precedence over .env)."""
    if os.environ.get("ESR_API_KEY"):
        return
    env_file = PROJECT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("ESR_API_KEY"):
                key = line.split("=", 1)[-1].strip()
                if key:
                    return
    print(
        "ERROR: ESR_API_KEY not set.\n"
        "  Set it via environment variable or add ESR_API_KEY=<key> to "
        f"{env_file}",
        file=sys.stderr,
    )
    sys.exit(1)


def db_latest_week() -> str | None:
    """Return the max week_ending across all commodities, or None."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT MAX(week_ending) FROM fact_esr_world_weekly"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def run(cmd: list[str], label: str) -> None:
    print(f"\n--- {label} ---")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print(f"ERROR: {label} exited {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    check_api_key()

    week_before = db_latest_week()
    print(f"DB latest week before refresh: {week_before or 'none'}")

    py = sys.executable
    run(
        [py, str(PROJECT_DIR / "batch_etl.py"), "--force-refresh"],
        "Step 1: refresh ESR database from USDA API",
    )

    week_after = db_latest_week()
    if week_after != week_before:
        print(f"DB updated: {week_before} → {week_after}")
    else:
        print(
            f"NOTE: DB week_ending unchanged ({week_after}). "
            "USDA API may not have released a newer week yet — "
            "check https://apps.fas.usda.gov/esrquery/esrq.aspx"
        )

    run(
        [py, str(PROJECT_DIR / "export_reporting_snapshot.py")],
        "Step 2: regenerate structured snapshot CSV",
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
