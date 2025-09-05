#!/usr/bin/env python3
"""
Enhanced multi-commodity wheat export pace comparison dashboard.
Shows both MY 2025 (All Wheat) and MY 2026 (individual classes) data.
"""

import sys
from pathlib import Path
import sqlite3
from datetime import datetime
import pandas as pd

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

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
    101: "Hard Red Winter",
    102: "Soft Red Winter", 
    103: "Hard Red Spring",
    104: "White Wheat",
    105: "Durum Wheat",
    107: "All Wheat (MY 2025)"
}

# Color palette for different wheat classes
WHEAT_COLORS = {
    101: BENDIGO_COLORS['primary'],    # Deep burgundy
    102: BENDIGO_COLORS['secondary'],  # Red  
    103: BENDIGO_COLORS['accent1'],    # Red variant
    104: BENDIGO_COLORS['accent2'],    # Orange
    105: BENDIGO_COLORS['accent3'],    # Light orange
    107: BENDIGO_COLORS['dark1'],      # Dark burgundy
}

def get_all_wheat_data():
    """Get comprehensive wheat data from both MY 2025 and MY 2026."""
    
    conn = sqlite3.connect('data/esr_data.db')
    
    # Get MY 2026 data for individual wheat classes (12 weeks)
    query_2026 = """
    SELECT commodity_code, market_year, week_ending, 
           accumulated_exports_mt, weekly_exports_mt
    FROM fact_esr_world_weekly 
    WHERE market_year = 2026 AND commodity_code != 107
    ORDER BY commodity_code, week_ending
    """
    
    # Get MY 2025 data for All Wheat (53 weeks)
    query_2025 = """
    SELECT commodity_code, market_year, week_ending, 
           accumulated_exports_mt, weekly_exports_mt
    FROM fact_esr_world_weekly 
    WHERE market_year = 2025 AND commodity_code = 107
    ORDER BY commodity_code, week_ending
    """
    
    data_2026 = pd.read_sql_query(query_2026, conn)
    data_2025 = pd.read_sql_query(query_2025, conn)
    
    print("📊 Available wheat export data:")
    print(f"   • MY 2026 (Individual Classes): {len(data_2026.commodity_code.unique())} commodities")
    for comm in sorted(data_2026.commodity_code.unique()):
        weeks = len(data_2026[data_2026.commodity_code == comm])
        latest = data_2026[data_2026.commodity_code == comm].accumulated_exports_mt.max() / 1e6
        print(f"     - {comm}: {WHEAT_COMMODITIES.get(comm, f'Code {comm}')} ({weeks} weeks, {latest:.2f}M MT)")
    
    print(f"   • MY 2025 (All Wheat): {len(data_2025)} weeks, {data_2025.accumulated_exports_mt.max()/1e6:.2f}M MT")
    
    conn.close()
    return data_2026, data_2025

def create_enhanced_comparison_dashboard():
    """Create comprehensive dashboard comparing all wheat classes."""
    
    print("🌾 Creating Enhanced Multi-Commodity Comparison Dashboard")
    print("=" * 65)
    
    # Get all data
    data_2026, data_2025 = get_all_wheat_data()
    
    if data_2026.empty and data_2025.empty:
        print("❌ No data available")
        return None
    
    # Create 2x2 dashboard
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "📈 Current Marketing Year Cumulative Exports",
            "🎯 Individual Wheat Classes (MY 2026)", 
            "📊 All Wheat Historical Performance (MY 2025)",
            "⚖️ Latest Week Export Comparison"
        ],
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"type": "bar"}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.10
    )
    
    summary_data = {}
    
    # 1. Combined view (Top Left) - All commodities on one chart
    
    # Add MY 2026 individual wheat classes
    for commodity in sorted(data_2026.commodity_code.unique()):
        comm_data = data_2026[data_2026.commodity_code == commodity].sort_values('week_ending')
        
        cumulative_mt = comm_data.accumulated_exports_mt / 1e6
        weeks = range(1, len(cumulative_mt) + 1)
        
        name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')
        color = WHEAT_COLORS.get(commodity, BENDIGO_COLORS['foreground'])
        
        summary_data[commodity] = {
            'name': name,
            'latest': cumulative_mt.iloc[-1] if len(cumulative_mt) > 0 else 0,
            'weeks': len(cumulative_mt),
            'my': '2026'
        }
        
        fig.add_trace(
            go.Scatter(
                x=list(weeks),
                y=cumulative_mt,
                mode='lines+markers',
                name=f'{name} (MY26)',
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
                hovertemplate=f'{name}<br>Week: %{{x}}<br>Cumulative: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Add All Wheat MY 2025 data
    if not data_2025.empty:
        cumulative_mt = data_2025.accumulated_exports_mt / 1e6
        weeks = range(1, len(cumulative_mt) + 1)
        
        name = "All Wheat"
        color = WHEAT_COLORS[107]
        
        summary_data[107] = {
            'name': name,
            'latest': cumulative_mt.iloc[-1],
            'weeks': len(cumulative_mt),
            'my': '2025'
        }
        
        fig.add_trace(
            go.Scatter(
                x=list(weeks),
                y=cumulative_mt,
                mode='lines+markers',
                name=f'{name} (MY25)',
                line=dict(color=color, width=3),
                marker=dict(size=6, color=color),
                hovertemplate=f'{name} MY25<br>Week: %{{x}}<br>Cumulative: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=1
        )
    
    # 2. Individual wheat classes detail (Top Right) - Focus on MY 2026
    max_weeks_2026 = 0
    for commodity in sorted(data_2026.commodity_code.unique()):
        comm_data = data_2026[data_2026.commodity_code == commodity].sort_values('week_ending')
        
        cumulative_mt = comm_data.accumulated_exports_mt / 1e6
        weeks = range(1, len(cumulative_mt) + 1)
        max_weeks_2026 = max(max_weeks_2026, len(weeks))
        
        name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')
        color = WHEAT_COLORS.get(commodity, BENDIGO_COLORS['foreground'])
        
        fig.add_trace(
            go.Scatter(
                x=list(weeks),
                y=cumulative_mt,
                mode='lines+markers',
                name=name,
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color),
                showlegend=False,
                hovertemplate=f'{name}<br>Week: %{{x}}<br>Cumulative: %{{y:.2f}}M MT<extra></extra>'
            ),
            row=1, col=2
        )
    
    # 3. All Wheat historical view (Bottom Left) - MY 2025 detail
    if not data_2025.empty:
        # Show both cumulative and weekly exports
        cumulative_mt = data_2025.accumulated_exports_mt / 1e6
        weekly_mt = data_2025.weekly_exports_mt / 1e6
        weeks = range(1, len(cumulative_mt) + 1)
        
        # Cumulative line
        fig.add_trace(
            go.Scatter(
                x=list(weeks),
                y=cumulative_mt,
                mode='lines',
                name='Cumulative',
                line=dict(color=BENDIGO_COLORS['primary'], width=3),
                yaxis='y3',
                showlegend=False,
                hovertemplate='Week: %{x}<br>Cumulative: %{y:.2f}M MT<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Add weekly bars (secondary y-axis effect by scaling)
        weekly_scaled = weekly_mt * 10  # Scale for visibility
        fig.add_trace(
            go.Bar(
                x=list(weeks),
                y=weekly_scaled,
                name='Weekly (×10)',
                marker_color=BENDIGO_COLORS['accent3'],
                opacity=0.6,
                showlegend=False,
                hovertemplate='Week: %{x}<br>Weekly: %{customdata:.2f}M MT<extra></extra>',
                customdata=weekly_mt
            ),
            row=2, col=1
        )
    
    # 4. Latest week comparison (Bottom Right)
    commodities = list(summary_data.keys())
    names = [f"{summary_data[c]['name']} ({summary_data[c]['my']})" for c in commodities]
    latest_exports = [summary_data[c]['latest'] for c in commodities]
    colors = [WHEAT_COLORS.get(c, BENDIGO_COLORS['foreground']) for c in commodities]
    
    fig.add_trace(
        go.Bar(
            x=names,
            y=latest_exports,
            marker_color=colors,
            opacity=0.8,
            showlegend=False,
            hovertemplate='%{x}<br>Latest: %{y:.2f}M MT<extra></extra>'
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "🌾 Enhanced Multi-Commodity Wheat Export Dashboard<br><sub>MY 2025 (All Wheat Historical) + MY 2026 (Individual Classes Current)</sub>",
            'x': 0.5,
            'font': {'size': 16, 'color': BENDIGO_COLORS['primary']}
        },
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", 
            y=-0.12,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor=BENDIGO_COLORS['background'],
        paper_bgcolor=BENDIGO_COLORS['background']
    )
    
    # Update axis labels and formatting
    fig.update_xaxes(title_text="Marketing Week", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=1, col=1)
    
    fig.update_xaxes(title_text="Marketing Week", row=1, col=2)
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=1, col=2)
    
    fig.update_xaxes(title_text="Marketing Week", row=2, col=1)
    fig.update_yaxes(title_text="Exports (Million MT)", row=2, col=1)
    
    fig.update_xaxes(title_text="Wheat Class", row=2, col=2, tickangle=45)
    fig.update_yaxes(title_text="Latest Cumulative (Million MT)", row=2, col=2)
    
    # Save dashboard
    output_file = "output/enhanced_wheat_multi_commodity_comparison.html"
    fig.write_html(output_file)
    
    print(f"✅ Enhanced comparison dashboard saved to: {output_file}")
    
    # Summary
    print("\n📊 WHEAT EXPORT SUMMARY")
    print("=" * 50)
    
    total_individual_2026 = sum(data['latest'] for comm, data in summary_data.items() if data['my'] == '2026')
    
    print("MY 2026 Individual Classes (Current, 12 weeks):")
    individual_commodities = [(c, d) for c, d in summary_data.items() if d['my'] == '2026']
    individual_commodities.sort(key=lambda x: x[1]['latest'], reverse=True)
    
    for commodity, data in individual_commodities:
        percentage = (data['latest'] / total_individual_2026 * 100) if total_individual_2026 > 0 else 0
        print(f"  • {data['name']:20} | {data['latest']:5.2f}M MT | {percentage:5.1f}%")
    
    print(f"  {'─' * 45}")
    print(f"  {'TOTAL INDIVIDUAL':20} | {total_individual_2026:5.2f}M MT | 100.0%")
    
    if 107 in summary_data:
        all_wheat_data = summary_data[107]
        print(f"\n{all_wheat_data['name']} (Historical, {all_wheat_data['weeks']} weeks):")
        print(f"  • Complete marketing year | {all_wheat_data['latest']:5.2f}M MT")
    
    return output_file

if __name__ == "__main__":
    try:
        output_file = create_enhanced_comparison_dashboard()
        
        if output_file:
            print(f"\n🎉 Enhanced multi-commodity dashboard created!")
            print(f"📂 Open: {output_file}")
            print("\n💡 This dashboard provides:")
            print("   • Current MY 2026 individual wheat class performance (12 weeks)")
            print("   • Complete MY 2025 All Wheat historical data (53 weeks)")
            print("   • Side-by-side comparison of all wheat export activity")
            print("   • Latest week export totals across all classes")
            print(f"   • Beautiful Bendigo color theme 🎨")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()