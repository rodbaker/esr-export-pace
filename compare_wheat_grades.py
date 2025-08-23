#!/usr/bin/env python3
"""Compare performance across wheat grades."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esr_pace.pace_calc import PaceAnalyzer

def compare_wheat_grades():
    """Generate comparison analysis across wheat grades."""
    
    wheat_classes = {
        101: "Hard Red Winter (HRW)",
        102: "Soft Red Winter (SRW)", 
        103: "Hard Red Spring (HRS)",
        104: "White Wheat",
        105: "Durum Wheat",
        106: "Mixed Wheat",
        107: "All Wheat"
    }
    
    print("=== Wheat Grade Performance Comparison ===\n")
    
    analyzer = PaceAnalyzer("data/esr_data.db")
    results = []
    
    for commodity_code, name in wheat_classes.items():
        try:
            current_data = analyzer.get_current_year_data(commodity_code=commodity_code)
            if current_data.empty:
                print(f"⚠️  {name} ({commodity_code}): No current data available")
                continue
                
            pace_metrics = analyzer.calculate_pace_deviations(commodity_code=commodity_code)
            if not pace_metrics:
                print(f"⚠️  {name} ({commodity_code}): Unable to calculate pace metrics")
                continue
                
            summary = analyzer.get_pace_summary(pace_metrics)
            latest_metric = pace_metrics[-1]
            
            results.append({
                'code': commodity_code,
                'name': name,
                'market_year': current_data['market_year'].iloc[0],
                'weeks': len(current_data),
                'trend': summary.current_pace_trend,
                'avg_deviation': summary.avg_pace_deviation_pct,
                'latest_deviation': latest_metric.pace_deviation_pct,
                'volatility': summary.volatility_score,
                'weeks_ahead': summary.weeks_ahead_of_pace,
                'weeks_behind': summary.weeks_behind_pace,
                'total_weeks': summary.total_weeks_analyzed
            })
            
        except Exception as e:
            print(f"❌ {name} ({commodity_code}): Error - {e}")
    
    # Sort by average deviation (descending)
    results.sort(key=lambda x: x['avg_deviation'], reverse=True)
    
    print(f"\n📊 Performance Ranking (by average deviation vs 5-year baseline):\n")
    print(f"{'Rank':<4} {'Code':<4} {'Wheat Grade':<25} {'MY':<4} {'Trend':<7} {'Avg Dev':<8} {'Latest':<8} {'Volatility':<10} {'Performance'}")
    print("="*95)
    
    for i, result in enumerate(results, 1):
        trend_emoji = "🟢" if result['trend'] == "ahead" else "🔴" if result['trend'] == "behind" else "🟡"
        performance = f"{result['weeks_ahead']}/{result['total_weeks']} ahead"
        
        print(f"{i:<4} {result['code']:<4} {result['name']:<25} {result['market_year']:<4} "
              f"{trend_emoji}{result['trend']:<6} {result['avg_deviation']:+7.1f}% {result['latest_deviation']:+7.1f}% "
              f"{result['volatility']:<10.2f} {performance}")
    
    print(f"\n🎯 Key Insights:")
    
    # Best and worst performers
    if results:
        best = results[0]
        worst = results[-1]
        
        print(f"   🥇 Best Performer: {best['name']} ({best['avg_deviation']:+.1f}% avg deviation)")
        print(f"   🥉 Worst Performer: {worst['name']} ({worst['avg_deviation']:+.1f}% avg deviation)")
        
        # Volatility analysis
        high_vol = [r for r in results if r['volatility'] > 1.5]
        if high_vol:
            print(f"   ⚡ High Volatility: {', '.join([r['name'] for r in high_vol])}")
        
        # Consistent performers
        consistent = [r for r in results if abs(r['avg_deviation']) < 10 and r['volatility'] < 1.0]
        if consistent:
            print(f"   🎯 Most Consistent: {', '.join([r['name'] for r in consistent])}")
    
    print(f"\n📈 Available Dashboards:")
    for result in results:
        safe_name = result['name'].lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
        print(f"   • {result['name']}: output/pace_dashboard_{result['code']}_{result['market_year']}.html")
        print(f"   • Range Chart: output/{safe_name}_historical_range.html")

if __name__ == "__main__":
    compare_wheat_grades()