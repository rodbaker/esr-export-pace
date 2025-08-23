#!/usr/bin/env python3
"""Debug test for pace analysis."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from esr_pace.pace_calc import PaceAnalyzer

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def debug_baseline():
    """Debug baseline calculation."""
    
    analyzer = PaceAnalyzer(db_path="data/esr_data.db")
    
    print("=== DEBUGGING BASELINE CALCULATION ===")
    
    # Test the exact sequence that fails
    try:
        # 1. Get current year data for MY 2026
        print("\n1. Getting current year data for MY 2026...")
        df_current = analyzer.get_current_year_data(107, 2026)
        print(f"   Got {len(df_current)} weeks of data")
        print(f"   Market year: {df_current['market_year'].iloc[0]}")
        
        # 2. Try to get baseline for that year
        print(f"\n2. Getting baseline for MY {df_current['market_year'].iloc[0]}...")
        current_year = df_current['market_year'].iloc[0]
        df_baseline = analyzer.get_historical_baseline(107, current_year)
        print(f"   Got baseline with {len(df_baseline)} marketing weeks")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_baseline()