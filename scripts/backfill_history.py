#!/usr/bin/env python3
"""One-off historical backfill for new commodities (corn + soy complex)."""
import os
import sys
import logging
from pathlib import Path

# Ensure the project's src/ is importable when run from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logging.getLogger('urllib3').setLevel(logging.WARNING)

from src.esr_pace.etl import ESRETLPipeline

COMMODITIES = [401, 801, 901, 902]
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]


def main() -> int:
    api_key = os.getenv('ESR_API_KEY')
    if not api_key:
        print('ESR_API_KEY missing', file=sys.stderr)
        return 1
    pipe = ESRETLPipeline(api_key=api_key)
    summary = []
    for code in COMMODITIES:
        for my in YEARS:
            try:
                r = pipe.run_etl(commodity_code=code, target_market_year=my,
                                 validate_data=True, force_refresh=False)
                summary.append((code, my, bool(r.get('success')),
                                r.get('records_loaded'),
                                r.get('country_records_loaded'),
                                r.get('error')))
                print(f"  {code} MY{my}: ok={r['success']} "
                      f"world={r.get('records_loaded')} "
                      f"ctry={r.get('country_records_loaded')}")
            except Exception as e:  # pragma: no cover - operational
                summary.append((code, my, False, 0, 0, str(e)))
                print(f"  {code} MY{my}: EXC {e}")
    pipe.close()
    print("\n=== summary ===")
    for row in summary:
        print(row)
    return 0


if __name__ == '__main__':
    sys.exit(main())
