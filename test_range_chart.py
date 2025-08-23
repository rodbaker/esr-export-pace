#!/usr/bin/env python3
"""Test the new historical range chart functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esr_pace.pace_calc import PaceAnalyzer

def test_range_chart():
    print("=== Testing Historical Range Chart ===")
    
    try:
        # Initialize analyzer
        analyzer = PaceAnalyzer("data/esr_data.db")
        print("✅ PaceAnalyzer initialized successfully")
        
        # Create historical range chart
        print("\n📊 Creating historical range chart...")
        fig = analyzer.create_historical_range_chart(
            commodity_code=107,
            title="Wheat Export Historical Range Analysis"
        )
        
        # Save the chart
        output_file = "output/wheat_historical_range_chart.html"
        fig.write_html(output_file)
        print(f"✅ Chart saved to: {output_file}")
        
        # Get some basic stats for display
        print("\n📈 Chart Features:")
        print("   - Historical min/max range band (3-year: 2023-2025)")
        print("   - Historical average trend line")
        print("   - Current marketing year (2026) overlay line")
        print("   - Interactive tooltips with week details")
        print("   - Position annotation (above/below/within range)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_range_chart()
    sys.exit(0 if success else 1)