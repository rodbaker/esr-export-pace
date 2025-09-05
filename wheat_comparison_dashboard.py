#!/usr/bin/env python3
"""
Create a comprehensive multi-commodity wheat export pace comparison dashboard.
Uses the existing working pace analysis functions.
"""

import sys
from pathlib import Path
import sqlite3
from datetime import datetime
import pandas as pd

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from esr_pace.pace_calc import PaceAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

def get_commodity_data_direct():
    """Get commodity data directly from database."""
    
    conn = sqlite3.connect('data/esr_data.db')
    
    # Get current year data for all commodities
    query_current = """
    SELECT commodity_code, market_year, week_ending, 
           accumulated_exports_mt, weekly_exports_mt
    FROM fact_esr_world_weekly 
    WHERE market_year = 2025
    ORDER BY commodity_code, week_ending
    """
    
    current_data = pd.read_sql_query(query_current, conn)
    
    # Get available commodities with sufficient current data
    commodity_counts = current_data.groupby('commodity_code').size()
    available_commodities = commodity_counts[commodity_counts >= 8].index.tolist()
    
    print(f"📊 Found {len(available_commodities)} commodities with sufficient current data:")
    for comm in available_commodities:
        name = WHEAT_COMMODITIES.get(comm, f'Code {comm}')
        weeks = commodity_counts[comm]
        print(f"   • {comm}: {name} ({weeks} weeks)")
    
    conn.close()
    return current_data, available_commodities

def create_simple_comparison_dashboard():
    """Create a simplified comparison dashboard using direct database access."""
    
    print("🌾 Creating Simplified Multi-Commodity Comparison Dashboard")
    print("=" * 60)
    
    # Get data directly
    current_data, available_commodities = get_commodity_data_direct()
    
    if len(available_commodities) == 0:
        print("❌ No commodities with sufficient data found")
        return None
    
    # Create the dashboard
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "📈 Cumulative Export Comparison (MY 2025)",
            "📊 Latest Week Exports by Wheat Class", 
            "🎯 Export Progression Over Marketing Weeks",
            "📈 Weekly Growth Rates"
        ],
        specs=[
            [{"secondary_y": False}, {"type": "bar"}],
            [{"secondary_y": False}, {"secondary_y": False}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.10
    )
    
    commodity_summary = {}
    
    # 1. Cumulative Export Comparison (Top Left)
    color_idx = 0
    for commodity in available_commodities:
        comm_data = current_data[current_data['commodity_code'] == commodity].copy()
        comm_data = comm_data.sort_values('week_ending')
        
        commodity_name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')
        color = WHEAT_COLORS[color_idx % len(WHEAT_COLORS)]
        
        # Convert to million MT and calculate weeks
        cumulative_mt = comm_data['accumulated_exports_mt'] / 1e6
        weeks = range(1, len(cumulative_mt) + 1)
        
        # Store summary data
        commodity_summary[commodity] = {
            'name': commodity_name,
            'latest_cumulative': cumulative_mt.iloc[-1] if len(cumulative_mt) > 0 else 0,
            'total_weeks': len(cumulative_mt),
            'color': color,
            'weekly_data': cumulative_mt.tolist()
        }
        
        fig.add_trace(
            go.Scatter(
                x=list(weeks),
                y=cumulative_mt,
                mode='lines+markers',
                name=commodity_name,
                line=dict(color=color, width=3),
                marker=dict(size=6, color=color),
                hovertemplate=f'{commodity_name}<br>Week: %{{x}}<br>Cumulative: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=1
        )
        
        color_idx += 1
    
    # 2. Latest Week Exports Bar Chart (Top Right)
    commodities = list(commodity_summary.keys())
    commodity_names = [commodity_summary[c]['name'] for c in commodities]
    latest_exports = [commodity_summary[c]['latest_cumulative'] for c in commodities]
    colors = [commodity_summary[c]['color'] for c in commodities]
    
    fig.add_trace(
        go.Bar(
            x=commodity_names,
            y=latest_exports,
            marker_color=colors,
            name='Latest Cumulative',
            opacity=0.8,
            hovertemplate='%{x}<br>Cumulative: %{y:.2f}M MT<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 3. Export Progression (Bottom Left) - Show all as area plot
    max_weeks = max(commodity_summary[c]['total_weeks'] for c in commodities)
    weeks_range = list(range(1, max_weeks + 1))
    
    for commodity in commodities:
        data = commodity_summary[commodity]
        name = data['name']
        color = data['color']
        
        # Pad data to max weeks
        weekly_data = data['weekly_data']
        if len(weekly_data) < max_weeks:
            weekly_data.extend([weekly_data[-1]] * (max_weeks - len(weekly_data)))
        
        fig.add_trace(
            go.Scatter(
                x=weeks_range,
                y=weekly_data,
                mode='lines',
                name=name,
                line=dict(color=color, width=2),
                fill='tonexty' if commodity != commodities[0] else 'tozeroy',
                fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3)',
                showlegend=False,
                hovertemplate=f'{name}<br>Week: %{{x}}<br>Cumulative: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=2, col=1
        )
    
    # 4. Weekly Growth Analysis (Bottom Right)
    for commodity in commodities:
        comm_data = current_data[current_data['commodity_code'] == commodity].copy()
        comm_data = comm_data.sort_values('week_ending')
        
        if len(comm_data) > 1:
            # Calculate week-over-week growth
            cumulative = comm_data['accumulated_exports_mt'] / 1e6
            weekly_growth = cumulative.diff().fillna(0)  # Weekly incremental exports
            
            data = commodity_summary[commodity]
            name = data['name']
            color = data['color']
            
            weeks = range(1, len(weekly_growth) + 1)
            
            fig.add_trace(
                go.Scatter(
                    x=list(weeks),
                    y=weekly_growth,
                    mode='lines+markers',
                    name=name,
                    line=dict(color=color, width=2),
                    marker=dict(size=4, color=color),
                    showlegend=False,
                    hovertemplate=f'{name}<br>Week: %{{x}}<br>Weekly: %{{y:.2f}}M MT<extra></extra>'
                ),
                row=2, col=2
            )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "🌾 Multi-Commodity Wheat Export Comparison Dashboard<br><sub>Marketing Year 2025 - All Available Wheat Classes</sub>",
            'x': 0.5,
            'font': {'size': 18, 'color': BENDIGO_COLORS['primary']}
        },
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", 
            y=-0.15,
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
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=2, col=1)
    
    fig.update_xaxes(title_text="Marketing Week", row=2, col=2)  
    fig.update_yaxes(title_text="Weekly Exports (Million MT)", row=2, col=2)
    
    # Save the dashboard
    output_file = "output/wheat_multi_commodity_comparison.html"
    fig.write_html(output_file)
    
    print(f"✅ Multi-commodity comparison dashboard saved to: {output_file}")
    
    # Print summary
    print("\n📊 COMMODITY EXPORT SUMMARY (Latest Week)")
    print("=" * 55)
    
    # Sort by latest cumulative exports
    sorted_commodities = sorted(commodity_summary.items(), key=lambda x: x[1]['latest_cumulative'], reverse=True)
    
    total_exports = sum(data['latest_cumulative'] for _, data in sorted_commodities)
    
    for rank, (commodity, data) in enumerate(sorted_commodities, 1):
        name = data['name']
        latest = data['latest_cumulative']
        weeks = data['total_weeks']
        percentage = (latest / total_exports * 100) if total_exports > 0 else 0
        
        print(f"{rank}. {name:25} | {latest:6.2f}M MT | {weeks:2d} weeks | {percentage:5.1f}%")
    
    print(f"{'':31}{'─' * 35}")
    print(f"{'TOTAL':31} | {total_exports:6.2f}M MT |          | 100.0%")
    
    return output_file

if __name__ == "__main__":
    try:
        output_file = create_simple_comparison_dashboard()
        
        if output_file:
            print(f"\n🎉 Multi-commodity comparison dashboard created successfully!")
            print(f"📂 Open: {output_file}")
            print("\n💡 This dashboard shows:")
            print("   • Cumulative export comparison across all wheat classes")
            print("   • Latest week export totals by commodity") 
            print("   • Export progression over marketing weeks")
            print("   • Weekly growth patterns for each wheat class")
            print("\nUsing your custom Bendigo color theme! 🎨")
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error creating comparison dashboard: {e}")
        import traceback
        traceback.print_exc()