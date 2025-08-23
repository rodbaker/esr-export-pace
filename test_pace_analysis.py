#!/usr/bin/env python3
"""Test the pace analysis functionality."""

import sys
from src.esr_pace.pace_calc import PaceAnalyzer

def test_pace_analysis():
    print("=== Testing ESR Pace Analysis ===")
    
    try:
        # Initialize analyzer
        analyzer = PaceAnalyzer("data/esr_data.db")
        print("✅ PaceAnalyzer initialized successfully")
        
        # Test current year data retrieval
        current_data = analyzer.get_current_year_data(commodity_code=107)
        print(f"✅ Current year data: {len(current_data)} weeks")
        print(f"   Date range: {current_data['week_ending'].min()} to {current_data['week_ending'].max()}")
        
        # Test historical baseline calculation
        baseline = analyzer.get_historical_baseline(commodity_code=107)
        print(f"✅ Historical baseline: {len(baseline)} marketing weeks")
        print(f"   Example baseline week 1: {baseline[baseline['marketing_week_index'] == 1][['weekly_exports_mt_mean', 'accumulated_exports_mt_mean']].values}")
        
        # Calculate pace deviations
        pace_metrics = analyzer.calculate_pace_deviations(commodity_code=107)
        print(f"✅ Pace deviations calculated: {len(pace_metrics)} weeks")
        
        # Show first few weeks
        print("\\n📊 Sample Pace Analysis (First 3 Weeks):")
        for i, metric in enumerate(pace_metrics[:3]):
            print(f"   Week {metric.marketing_week} ({metric.week_ending}):")
            print(f"     Current: {metric.current_accumulated/1e6:.2f}M MT")
            print(f"     Historical: {metric.historical_avg_accumulated/1e6:.2f}M MT") 
            print(f"     Deviation: {metric.pace_deviation_pct:+.1f}% ({analyzer.classify_deviation_severity(metric.pace_deviation_pct)})")
        
        # Generate summary
        summary = analyzer.get_pace_summary(pace_metrics)
        print(f"\\n📈 Pace Summary:")
        print(f"   Current Trend: {summary.current_pace_trend.upper()}")
        print(f"   Weeks Ahead: {summary.weeks_ahead_of_pace}/{summary.total_weeks_analyzed}")
        print(f"   Weeks Behind: {summary.weeks_behind_pace}/{summary.total_weeks_analyzed}")
        print(f"   Average Deviation: {summary.avg_pace_deviation_pct:+.1f}%")
        print(f"   Volatility Score: {summary.volatility_score:.2f}")
        
        if summary.outlier_weeks:
            print(f"   Outlier Weeks: {summary.outlier_weeks}")
        
        # Generate full report
        report = analyzer.generate_pace_report(commodity_code=107, save_charts=True, output_dir="output")
        print(f"\\n✅ Full report generated with {len(report['key_insights'])} insights and {len(report['recommendations'])} recommendations")
        
        if 'charts' in report and report['charts']:
            print(f"   Charts saved:")
            for chart_type, path in report['charts'].items():
                print(f"     - {chart_type}: {path}")
        
        # Print executive summary
        analyzer.print_executive_summary(report)
        
        # Export to JSON
        json_file = analyzer.export_report_to_json(report, "output/pace_analysis_report.json")
        print(f"\\n💾 Full report exported to: {json_file}")
        
        # Generate historical range chart
        print(f"\\n📊 Creating historical range chart...")
        range_chart = analyzer.create_historical_range_chart(
            commodity_code=107,
            title="Wheat Export Historical Range Analysis"
        )
        range_chart_file = "output/wheat_historical_range.html"
        range_chart.write_html(range_chart_file)
        print(f"✅ Historical range chart saved to: {range_chart_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pace_analysis()
    sys.exit(0 if success else 1)