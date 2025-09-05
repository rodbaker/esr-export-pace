#!/usr/bin/env python3
"""
Create a comprehensive multi-commodity wheat export pace comparison dashboard.
Shows all wheat classes on a single page for easy comparison.
"""

import sys
from pathlib import Path
import logging
import sqlite3
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from esr_pace.pace_calc import PaceAnalyzer
from esr_pace.data_store import ESRDataStore
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# Bendigo Color Theme
BENDIGO_COLORS = {
    'primary': '#870E40',      # Deep burgundy
    'secondary': '#DE313B',    # Red
    'accent1': '#DB3929',      # Red variant
    'accent2': '#F37021',      # Orange
    'accent3': '#F7966B',      # Light orange
    'dark1': '#58003A',        # Dark burgundy
    'dark2': '#330019',        # Very dark burgundy
    'background': '#FFFFFF',   # White
    'foreground': '#323D42',   # Dark gray
    'light1': '#CBCCCC',       # Light gray
    'light2': '#E2E7E9',       # Very light gray
}

# Wheat commodity mapping
WHEAT_COMMODITIES = {
    101: "Hard Red Winter (HRW)",
    102: "Soft Red Winter (SRW)", 
    103: "Hard Red Spring (HRS)",
    104: "White Wheat",
    105: "Durum Wheat",
    107: "All Wheat"
}

# Color palette for different wheat classes
WHEAT_COLORS = [
    BENDIGO_COLORS['primary'],    # 101 - Deep burgundy
    BENDIGO_COLORS['secondary'],  # 102 - Red  
    BENDIGO_COLORS['accent1'],    # 103 - Red variant
    BENDIGO_COLORS['accent2'],    # 104 - Orange
    BENDIGO_COLORS['accent3'],    # 105 - Light orange
    BENDIGO_COLORS['dark1'],      # 107 - Dark burgundy
]

def get_available_commodities():
    """Get list of available wheat commodities with data."""
    conn = sqlite3.connect('data/esr_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT commodity_code, COUNT(*) as weeks 
        FROM fact_esr_world_weekly 
        WHERE market_year = 2026 
        GROUP BY commodity_code 
        HAVING weeks >= 5
        ORDER BY commodity_code
    ''')
    
    commodities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return commodities

def create_multi_commodity_comparison():
    """Create comprehensive multi-commodity comparison dashboard."""
    
    print("🌾 Creating Multi-Commodity Wheat Export Pace Comparison Dashboard")
    print("=" * 70)
    
    # Initialize analyzer
    analyzer = PaceAnalyzer()
    
    # Get available commodities
    available_commodities = get_available_commodities()
    print(f"📊 Found {len(available_commodities)} wheat commodities with sufficient data")
    
    # Collect data for all commodities
    commodity_data = {}
    commodity_metrics = {}
    
    for commodity in available_commodities:
        try:
            print(f"   Processing {commodity}: {WHEAT_COMMODITIES.get(commodity, f'Commodity {commodity}')}...")
            
            # Get pace data
            current_year_data = analyzer.get_current_year_data(commodity)
            if current_year_data is None or current_year_data.empty:
                continue
                
            historical_baseline = analyzer.get_historical_baseline(commodity)
            if historical_baseline is None or historical_baseline.empty:
                continue
                
            pace_metrics = analyzer.calculate_pace_deviations(current_year_data, historical_baseline)
            if not pace_metrics:
                continue
                
            commodity_data[commodity] = {
                'current_data': current_year_data,
                'baseline': historical_baseline,
                'pace_metrics': pace_metrics
            }
            
            # Calculate summary statistics
            deviations = [m.pace_deviation_pct for m in pace_metrics]
            weeks_ahead = sum(1 for d in deviations if d > 0)
            avg_deviation = sum(deviations) / len(deviations)
            latest_deviation = deviations[-1] if deviations else 0
            
            commodity_metrics[commodity] = {
                'avg_deviation': avg_deviation,
                'latest_deviation': latest_deviation,
                'weeks_ahead': weeks_ahead,
                'total_weeks': len(deviations),
                'volatility': analyzer.calculate_volatility_score(deviations)
            }
            
        except Exception as e:
            print(f"   ❌ Error processing {commodity}: {e}")
            continue
    
    if not commodity_data:
        print("❌ No commodity data available for comparison")
        return
        
    print(f"✅ Successfully processed {len(commodity_data)} commodities")
    
    # Create the comprehensive dashboard
    create_comparison_dashboard(commodity_data, commodity_metrics)

def create_comparison_dashboard(commodity_data, commodity_metrics):
    """Create the main comparison dashboard."""
    
    # Create subplot layout: 2x2 grid
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "📈 Cumulative Export Pace Comparison",
            "📊 Current vs Historical Performance", 
            "🎯 Weekly Pace Deviations",
            "📈 Performance Summary"
        ],
        specs=[
            [{"secondary_y": False}, {"type": "bar"}],
            [{"secondary_y": False}, {"type": "table"}]
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.08
    )
    
    # 1. Cumulative Export Pace Comparison (Top Left)
    color_idx = 0
    for commodity, data in commodity_data.items():
        pace_metrics = data['pace_metrics']
        
        weeks = [m.marketing_week for m in pace_metrics]
        cumulative_current = [m.current_accumulated / 1e6 for m in pace_metrics]  # Convert to millions MT
        cumulative_baseline = [m.historical_avg_accumulated / 1e6 for m in pace_metrics]
        
        commodity_name = WHEAT_COMMODITIES.get(commodity, f'Commodity {commodity}')
        color = WHEAT_COLORS[color_idx % len(WHEAT_COLORS)]
        
        # Current year line
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=cumulative_current,
                mode='lines+markers',
                name=f'{commodity_name} (Current)',
                line=dict(color=color, width=3),
                marker=dict(size=6, color=color),
                showlegend=True,
                hovertemplate=f'{commodity_name}<br>Week: %{{x}}<br>Current: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Historical baseline (dashed)
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=cumulative_baseline,
                mode='lines',
                name=f'{commodity_name} (Baseline)',
                line=dict(color=color, width=2, dash='dash'),
                opacity=0.7,
                showlegend=False,
                hovertemplate=f'{commodity_name} Baseline<br>Week: %{{x}}<br>Baseline: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=1
        )
        
        color_idx += 1
    
    # 2. Current vs Historical Performance Bar Chart (Top Right)
    commodities = list(commodity_metrics.keys())
    commodity_names = [WHEAT_COMMODITIES.get(c, f'Code {c}') for c in commodities]
    current_totals = []
    baseline_totals = []
    
    for commodity in commodities:
        data = commodity_data[commodity]
        pace_metrics = data['pace_metrics']
        current_totals.append(pace_metrics[-1].current_accumulated / 1e6)
        baseline_totals.append(pace_metrics[-1].historical_avg_accumulated / 1e6)
    
    fig.add_trace(
        go.Bar(
            x=commodity_names,
            y=current_totals,
            name='Current MY 2026',
            marker_color=BENDIGO_COLORS['primary'],
            opacity=0.8
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(
            x=commodity_names,
            y=baseline_totals,
            name='5-Year Baseline',
            marker_color=BENDIGO_COLORS['light1'],
            opacity=0.7
        ),
        row=1, col=2
    )
    
    # 3. Weekly Pace Deviations (Bottom Left)
    color_idx = 0
    for commodity, data in commodity_data.items():
        pace_metrics = data['pace_metrics']
        
        weeks = [m.marketing_week for m in pace_metrics]
        deviations = [m.pace_deviation_pct for m in pace_metrics]
        
        commodity_name = WHEAT_COMMODITIES.get(commodity, f'Commodity {commodity}')
        color = WHEAT_COLORS[color_idx % len(WHEAT_COLORS)]
        
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=deviations,
                mode='lines+markers',
                name=commodity_name,
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
                showlegend=False,
                hovertemplate=f'{commodity_name}<br>Week: %{{x}}<br>Deviation: %{{y:.1f}}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        color_idx += 1
    
    # Add zero line for reference
    fig.add_hline(y=0, line_dash="dot", line_color=BENDIGO_COLORS['light1'], row=2, col=1)
    
    # 4. Performance Summary Table (Bottom Right)
    table_data = []
    for commodity in commodities:
        metrics = commodity_metrics[commodity]
        commodity_name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')
        
        trend_emoji = "🟢" if metrics['avg_deviation'] > 5 else "🟡" if metrics['avg_deviation'] > -5 else "🔴"
        
        table_data.append([
            commodity_name,
            f"{metrics['avg_deviation']:+.1f}%",
            f"{metrics['latest_deviation']:+.1f}%",
            f"{metrics['weeks_ahead']}/{metrics['total_weeks']}",
            f"{metrics['volatility']:.2f}",
            trend_emoji
        ])
    
    fig.add_trace(
        go.Table(
            header=dict(
                values=['Wheat Grade', 'Avg Dev', 'Latest', 'Ahead', 'Volatility', 'Trend'],
                fill_color=BENDIGO_COLORS['primary'],
                font=dict(color='white', size=12),
                align='center'
            ),
            cells=dict(
                values=list(zip(*table_data)),
                fill_color=BENDIGO_COLORS['light2'],
                font=dict(color=BENDIGO_COLORS['foreground'], size=11),
                align='center'
            )
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "🌾 Multi-Commodity Wheat Export Pace Comparison Dashboard<br><sub>Marketing Year 2026 vs 5-Year Historical Baseline</sub>",
            'x': 0.5,
            'font': {'size': 20, 'color': BENDIGO_COLORS['primary']}
        },
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor=BENDIGO_COLORS['background'],
        paper_bgcolor=BENDIGO_COLORS['background']
    )
    
    # Update axis labels
    fig.update_xaxes(title_text="Marketing Week", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=1, col=1)
    
    fig.update_xaxes(title_text="Wheat Grade", row=1, col=2)
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=1, col=2)
    
    fig.update_xaxes(title_text="Marketing Week", row=2, col=1)
    fig.update_yaxes(title_text="Pace Deviation (%)", row=2, col=1)
    
    # Save the dashboard
    output_file = "output/wheat_multi_commodity_comparison.html"
    fig.write_html(output_file)
    
    print(f"✅ Multi-commodity comparison dashboard saved to: {output_file}")
    
    # Print summary
    print("\n📊 COMMODITY PERFORMANCE SUMMARY")
    print("=" * 50)
    
    # Sort by average deviation for ranking
    sorted_commodities = sorted(commodity_metrics.items(), key=lambda x: x[1]['avg_deviation'], reverse=True)
    
    for rank, (commodity, metrics) in enumerate(sorted_commodities, 1):
        commodity_name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')
        trend = "🟢ahead" if metrics['avg_deviation'] > 5 else "🟡on_pace" if metrics['avg_deviation'] > -5 else "🔴behind"
        
        print(f"{rank}. {commodity_name:25} | Avg: {metrics['avg_deviation']:+6.1f}% | Latest: {metrics['latest_deviation']:+6.1f}% | {trend}")
    
    return output_file

if __name__ == "__main__":
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        output_file = create_multi_commodity_comparison()
        
        print(f"\n🎉 Multi-commodity comparison dashboard created successfully!")
        print(f"📂 Open: {output_file}")
        print("\n💡 This dashboard shows:")
        print("   • Cumulative export pace comparison across all wheat classes")
        print("   • Current vs historical performance bars") 
        print("   • Weekly pace deviation trends")
        print("   • Performance summary table with rankings")
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error creating comparison dashboard: {e}")
        import traceback
        traceback.print_exc()