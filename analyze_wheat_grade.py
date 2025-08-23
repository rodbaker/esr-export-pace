#!/usr/bin/env python3
"""Generate pace analysis for specific wheat grades."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esr_pace.pace_calc import PaceAnalyzer

def analyze_wheat_grade(commodity_code, commodity_name=None):
    """Generate comprehensive analysis for a specific wheat grade."""
    
    print(f"=== {commodity_name or f'Commodity {commodity_code}'} Export Pace Analysis ===")
    
    try:
        # Initialize analyzer
        analyzer = PaceAnalyzer("data/esr_data.db")
        print("✅ PaceAnalyzer initialized successfully")
        
        # Test if we have data for this commodity
        current_data = analyzer.get_current_year_data(commodity_code=commodity_code)
        if current_data.empty:
            print(f"❌ No current year data found for commodity {commodity_code}")
            return False
            
        print(f"✅ Current year data: {len(current_data)} weeks")
        print(f"   Date range: {current_data['week_ending'].min()} to {current_data['week_ending'].max()}")
        
        # Calculate pace deviations
        pace_metrics = analyzer.calculate_pace_deviations(commodity_code=commodity_code)
        if not pace_metrics:
            print(f"❌ Unable to calculate pace deviations for commodity {commodity_code}")
            return False
            
        print(f"✅ Pace deviations calculated: {len(pace_metrics)} weeks")
        
        # Generate summary
        summary = analyzer.get_pace_summary(pace_metrics)
        print(f"\n📈 Pace Summary:")
        print(f"   Current Trend: {summary.current_pace_trend.upper()}")
        print(f"   Weeks Ahead: {summary.weeks_ahead_of_pace}/{summary.total_weeks_analyzed}")
        print(f"   Weeks Behind: {summary.weeks_behind_pace}/{summary.total_weeks_analyzed}")
        print(f"   Average Deviation: {summary.avg_pace_deviation_pct:+.1f}%")
        print(f"   Volatility Score: {summary.volatility_score:.2f}")
        
        if summary.outlier_weeks:
            print(f"   Outlier Weeks: {summary.outlier_weeks}")
        
        # Generate full report
        report = analyzer.generate_pace_report(commodity_code=commodity_code, save_charts=True, output_dir="output")
        print(f"\n✅ Full report generated with {len(report['key_insights'])} insights and {len(report['recommendations'])} recommendations")
        
        if 'charts' in report and report['charts']:
            print(f"   Charts saved:")
            for chart_type, path in report['charts'].items():
                print(f"     - {chart_type}: {path}")
        
        # Generate historical range chart
        print(f"\n📊 Creating historical range chart...")
        range_chart = analyzer.create_historical_range_chart(
            commodity_code=commodity_code,
            title=f"{commodity_name or f'Commodity {commodity_code}'} Export Historical Range Analysis"
        )
        range_chart_file = f"output/{commodity_name.lower().replace(' ', '_').replace('-', '_') if commodity_name else f'commodity_{commodity_code}'}_historical_range.html"
        range_chart.write_html(range_chart_file)
        print(f"✅ Historical range chart saved to: {range_chart_file}")
        
        # Print executive summary
        analyzer.print_executive_summary(report)
        
        # Export to JSON
        json_file = f"output/{commodity_name.lower().replace(' ', '_').replace('-', '_') if commodity_name else f'commodity_{commodity_code}'}_analysis_report.json"
        analyzer.export_report_to_json(report, json_file)
        print(f"\n💾 Full report exported to: {json_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Wheat class mapping
    wheat_classes = {
        101: "Hard Red Winter",
        102: "Soft Red Winter", 
        103: "Hard Red Spring",
        104: "White Wheat",
        105: "Durum Wheat",
        106: "Mixed Wheat",
        107: "All Wheat"
    }
    
    if len(sys.argv) > 1:
        try:
            commodity_code = int(sys.argv[1])
            commodity_name = wheat_classes.get(commodity_code, f"Commodity {commodity_code}")
        except ValueError:
            print("Usage: python analyze_wheat_grade.py [commodity_code]")
            print("Available wheat classes:")
            for code, name in wheat_classes.items():
                print(f"  {code}: {name}")
            sys.exit(1)
    else:
        print("Available wheat classes:")
        for code, name in wheat_classes.items():
            print(f"  {code}: {name}")
        print("\nUsage: python analyze_wheat_grade.py [commodity_code]")
        sys.exit(0)
    
    success = analyze_wheat_grade(commodity_code, commodity_name)
    sys.exit(0 if success else 1)