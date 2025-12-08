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
import yaml

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
    107: "All Wheat"
}

# Short codes for charts
WHEAT_SHORT_CODES = {
    101: "HRW",
    102: "SRW",
    103: "HRS",
    104: "White",
    105: "Durum",
    107: "All Wheat"
}

# Color palette for different wheat classes - Flat, professional
WHEAT_COLORS = {
    101: BENDIGO_COLORS['primary'],    # HRW - Deep burgundy (primary)
    102: BENDIGO_COLORS['secondary'],  # SRW - Red
    103: BENDIGO_COLORS['accent2'],    # HRS - Orange
    104: BENDIGO_COLORS['accent1'],    # White - Red variant
    105: BENDIGO_COLORS['accent3'],    # Durum - Light orange
    107: BENDIGO_COLORS['primary'],    # All Wheat - Deep burgundy (primary)
}

def get_all_wheat_data():
    """Get comprehensive wheat data including historical context."""

    conn = sqlite3.connect('data/esr_data.db')

    # Get MY 2026 data for ALL wheat commodities (including commitments)
    query_2026 = """
    SELECT commodity_code, market_year, week_ending,
           accumulated_exports_mt, weekly_exports_mt,
           outstanding_sales_mt, total_commitment_mt
    FROM fact_esr_world_weekly
    WHERE market_year = 2026
    ORDER BY commodity_code, week_ending
    """

    # Get All Wheat (107) historical data for past 6 years (2020-2025)
    query_all_wheat_historical = """
    SELECT commodity_code, market_year, week_ending,
           accumulated_exports_mt, weekly_exports_mt,
           outstanding_sales_mt, total_commitment_mt,
           ROW_NUMBER() OVER (PARTITION BY market_year ORDER BY week_ending) as week_number
    FROM fact_esr_world_weekly
    WHERE commodity_code = 107 AND market_year >= 2020
    ORDER BY market_year, week_ending
    """

    data_2026 = pd.read_sql_query(query_2026, conn)
    all_wheat_historical = pd.read_sql_query(query_all_wheat_historical, conn)

    print("📊 Available wheat export data:")
    print(f"   • MY 2026 (Current): {len(data_2026.commodity_code.unique())} commodities")
    for comm in sorted(data_2026.commodity_code.unique()):
        comm_data = data_2026[data_2026.commodity_code == comm]
        weeks = len(comm_data)
        latest_exports = comm_data.accumulated_exports_mt.max() / 1e6
        latest_commitments = comm_data.total_commitment_mt.max() / 1e6 if 'total_commitment_mt' in comm_data.columns else 0
        print(f"     - {comm}: {WHEAT_COMMODITIES.get(comm, f'Code {comm}')} ({weeks} weeks, {latest_exports:.2f}M MT exports, {latest_commitments:.2f}M MT commitments)")

    print(f"\n   • All Wheat Historical Data:")
    for my in sorted(all_wheat_historical.market_year.unique(), reverse=True):
        my_data = all_wheat_historical[all_wheat_historical.market_year == my]
        weeks = len(my_data)
        latest = my_data.accumulated_exports_mt.max() / 1e6
        print(f"     - MY {my}: {weeks} weeks, {latest:.2f}M MT")

    conn.close()
    return data_2026, all_wheat_historical


def calculate_historical_stats(all_wheat_historical, years_for_avg=[2020, 2021, 2022, 2023, 2024]):
    """Calculate 5-year average and range for All Wheat exports."""

    stats = {}

    # Get max week number to process
    max_weeks = all_wheat_historical.groupby('market_year').size().max()

    for week in range(1, max_weeks + 1):
        week_data = all_wheat_historical[
            (all_wheat_historical.week_number == week) &
            (all_wheat_historical.market_year.isin(years_for_avg))
        ]

        if len(week_data) > 0:
            stats[week] = {
                'avg': week_data.accumulated_exports_mt.mean(),
                'min': week_data.accumulated_exports_mt.min(),
                'max': week_data.accumulated_exports_mt.max(),
                'count': len(week_data)
            }

    return stats


def load_usda_estimates(commodity_code=107, market_year=2026):
    """Load USDA export estimates from configuration file."""

    config_path = Path(__file__).parent / 'config' / 'usda_estimates.yaml'

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        for estimate in config.get('estimates', []):
            if (estimate['commodity_code'] == commodity_code and
                estimate['market_year'] == market_year):
                return estimate

        print(f"⚠️  No USDA estimate found for commodity {commodity_code}, MY {market_year}")
        return None

    except FileNotFoundError:
        print(f"⚠️  USDA estimates config file not found: {config_path}")
        return None
    except Exception as e:
        print(f"⚠️  Error loading USDA estimates: {e}")
        return None

def create_enhanced_comparison_dashboard():
    """Create comprehensive dashboard comparing all wheat classes."""
    
    print("🌾 Creating Enhanced Multi-Commodity Comparison Dashboard")
    print("=" * 65)
    
    # Get all data
    data_2026, all_wheat_historical = get_all_wheat_data()

    if data_2026.empty and all_wheat_historical.empty:
        print("❌ No data available")
        return None

    # Calculate 5-year historical statistics for All Wheat
    historical_stats = calculate_historical_stats(all_wheat_historical, years_for_avg=[2020, 2021, 2022, 2023, 2024])

    # Load USDA export estimate
    usda_estimate = load_usda_estimates(commodity_code=107, market_year=2026)
    
    # Create 2x2 dashboard with visual hierarchy (larger top-left)
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "<b>Full Season Pace to USDA Estimate</b>",
            "<b>Sales Pipeline</b>",
            "<b>Exports by Wheat Class</b>",
            "<b>Progress Toward USDA Target (24.5 MMT)</b>"
        ],
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"type": "bar"}, {"secondary_y": False}]
        ],
        column_widths=[0.62, 0.38],  # Adjusted: give 62% to left, 38% to right (tighter)
        row_heights=[0.55, 0.45],    # Give 55% height to top row
        vertical_spacing=0.12,
        horizontal_spacing=0.06      # Reduced from 0.08 to 0.06 (~25% tighter)
    )
    
    summary_data = {}

    # 1. All Wheat with Historical Context (Top Left)
    # Show MY 2026 vs MY 2025 vs 5-year average/range

    # Extract All Wheat data
    all_wheat_2026 = data_2026[data_2026.commodity_code == 107].sort_values('week_ending')
    all_wheat_2025 = all_wheat_historical[all_wheat_historical.market_year == 2025].sort_values('week_ending')

    # Get current year data
    if not all_wheat_2026.empty:
        current_weeks = len(all_wheat_2026)
        current_cumulative = all_wheat_2026.accumulated_exports_mt.values / 1e6
        current_week_nums = list(range(1, current_weeks + 1))

        summary_data[107] = {
            'name': 'All Wheat',
            'latest': current_cumulative[-1],
            'weeks': current_weeks,
            'my': '2026'
        }
    else:
        current_weeks = 0

    # USDA Estimate Pace Line (full season target)
    if usda_estimate:
        estimate_mt = usda_estimate['estimate_mt'] / 1e6
        # Linear pace: week 0 = 0, week 53 = estimate
        pace_weeks = list(range(0, 54))
        pace_values = [estimate_mt * (w / 53) for w in pace_weeks]

        fig.add_trace(
            go.Scatter(
                x=pace_weeks,
                y=pace_values,
                mode='lines',
                name=f'USDA Estimate ({estimate_mt:.1f}M MT)',
                line=dict(color='#000000', width=1.5, dash='dot'),
                opacity=0.7,
                hovertemplate='Week: %{x}<br>Required Pace: %{y:.2f}M MT<extra></extra>'
            ),
            row=1, col=1
        )

    # Plot 5-year range (shaded area) - FULL SEASON
    if historical_stats:
        weeks = sorted(historical_stats.keys())  # Show all 53 weeks
        avg_values = [historical_stats[w]['avg'] / 1e6 for w in weeks]
        min_values = [historical_stats[w]['min'] / 1e6 for w in weeks]
        max_values = [historical_stats[w]['max'] / 1e6 for w in weeks]

        # 5-year range band - improved contrast
        fig.add_trace(
            go.Scatter(
                x=weeks + weeks[::-1],
                y=max_values + min_values[::-1],
                fill='toself',
                fillcolor='rgba(230, 230, 230, 0.55)',  # #E6E6E6 at 55% opacity
                line=dict(color='rgba(230, 230, 230, 0)'),
                name='5-Yr Range (2020-2024)',
                hoverinfo='skip',
                showlegend=True
            ),
            row=1, col=1
        )

        # 5-year average with dot markers - darker outline for better contrast
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=avg_values,
                mode='lines+markers',
                name='5-Yr Average',
                line=dict(color='#999999', width=1.3),
                marker=dict(size=3, color='#999999', symbol='circle'),
                hovertemplate='Week: %{x}<br>5-Yr Avg: %{y:.2f}M MT<extra></extra>'
            ),
            row=1, col=1
        )

    # Plot MY 2025 (last year) - FULL SEASON for context
    if not all_wheat_2025.empty:
        last_year_cumulative = all_wheat_2025.accumulated_exports_mt.values / 1e6
        last_year_weeks = list(range(1, len(last_year_cumulative) + 1))

        fig.add_trace(
            go.Scatter(
                x=last_year_weeks,
                y=last_year_cumulative,
                mode='lines',
                name='MY 2025',
                line=dict(color=BENDIGO_COLORS['light1'], width=2.5, dash='dash'),
                hovertemplate='Week: %{x}<br>MY 2025: %{y:.2f}M MT<extra></extra>',
                opacity=0.7
            ),
            row=1, col=1
        )

    # Plot MY 2026 (current year - bold and prominent)
    if not all_wheat_2026.empty:
        fig.add_trace(
            go.Scatter(
                x=current_week_nums,
                y=current_cumulative,
                mode='lines+markers',
                name='MY 2026 Actual',
                line=dict(color=BENDIGO_COLORS['primary'], width=2.8),
                marker=dict(size=6, color=BENDIGO_COLORS['primary'], line=dict(color='white', width=1)),
                hovertemplate='<b>MY 2026 Actual</b><br>Week: %{x}<br>Exports: %{y:.2f}M MT<extra></extra>'
            ),
            row=1, col=1
        )

        # Add simple dotted line to USDA estimate target
        if current_weeks >= 2 and usda_estimate:
            current_total = current_cumulative[-1]
            estimate_mt = usda_estimate['estimate_mt'] / 1e6

            # Simple projection line from current week to Week 53 at USDA target
            fig.add_trace(
                go.Scatter(
                    x=[current_weeks, 53],
                    y=[current_total, estimate_mt],
                    mode='lines',
                    name=f'Path to USDA Target ({estimate_mt:.1f}M MT)',
                    line=dict(color=BENDIGO_COLORS['primary'], width=1.5, dash='dot'),
                    hovertemplate='Week: %{x}<br>Target Path: %{y:.2f}M MT<extra></extra>',
                    opacity=0.6,
                    showlegend=True
                ),
                row=1, col=1
            )

            # Set projected_final for console output
            projected_final = estimate_mt
    
    # 2. Populate summary data for individual wheat classes (for later use)
    for commodity in sorted(data_2026.commodity_code.unique()):
        if commodity == 107:
            continue

        comm_data = data_2026[data_2026.commodity_code == commodity].sort_values('week_ending')
        cumulative_mt = comm_data.accumulated_exports_mt / 1e6
        name = WHEAT_COMMODITIES.get(commodity, f'Code {commodity}')

        # Add to summary data
        summary_data[commodity] = {
            'name': name,
            'latest': cumulative_mt.iloc[-1] if len(cumulative_mt) > 0 else 0,
            'weeks': len(cumulative_mt),
            'my': '2026'
        }

    # 3. Sales Pipeline breakdown (Row 1, Col 2) - Color grammar: burgundy=actual, orange=outstanding, grey=total
    if not all_wheat_2026.empty and 'outstanding_sales_mt' in all_wheat_2026.columns:
        latest_exports = all_wheat_2026.accumulated_exports_mt.iloc[-1] / 1e6
        latest_outstanding = all_wheat_2026.outstanding_sales_mt.iloc[-1] / 1e6

        pipeline_categories = ['Shipped', 'Outstanding', 'Total']
        pipeline_values = [latest_exports, latest_outstanding, latest_exports + latest_outstanding]
        pipeline_colors = [BENDIGO_COLORS['primary'], BENDIGO_COLORS['accent2'], '#5F6C7A']  # Lighter total bar

        fig.add_trace(
            go.Bar(
                x=pipeline_categories,
                y=pipeline_values,
                marker_color=pipeline_colors,
                showlegend=False,
                text=[f'<b>{v:.1f}M</b>' for v in pipeline_values],
                textposition='outside',
                textfont=dict(size=12, color=BENDIGO_COLORS['foreground']),
                hovertemplate='<b>%{x}</b><br>%{y:.2f}M MT<extra></extra>'
            ),
            row=1, col=2
        )

    # 4. Latest week comparison (Row 2, Col 1) - Flat colors, no gradients
    commodities = [c for c in summary_data.keys() if c != 105]  # Exclude Durum
    short_names = [WHEAT_SHORT_CODES.get(c, str(c)) for c in commodities]
    latest_exports = [summary_data[c]['latest'] for c in commodities]
    colors = [WHEAT_COLORS.get(c, BENDIGO_COLORS['foreground']) for c in commodities]
    full_names = [WHEAT_COMMODITIES.get(c, str(c)) for c in commodities]

    # Bars with flat color
    fig.add_trace(
        go.Bar(
            x=short_names,
            y=latest_exports,
            marker_color=colors,
            showlegend=False,
            text=[f'<b>{v:.1f}M</b>' for v in latest_exports],
            textposition='outside',
            textfont=dict(size=12, color=BENDIGO_COLORS['foreground'], family='Arial'),
            hovertemplate='<b>%{customdata}</b><br>Exports: %{y:.2f}M MT<extra></extra>',
            customdata=full_names
        ),
        row=2, col=1
    )

    # Add 5-year average markers as diamonds on all bars
    if historical_stats and current_weeks in historical_stats:
        avg_at_current_week = historical_stats[current_weeks]['avg'] / 1e6
        # Show marker for All Wheat only (individual class averages would require separate historical data)
        avg_markers = []
        for c in commodities:
            if c == 107:  # Only show for All Wheat
                avg_markers.append(avg_at_current_week)
            else:
                avg_markers.append(None)

        fig.add_trace(
            go.Scatter(
                x=short_names,
                y=[avg_at_current_week if c == 107 else None for c in commodities],
                mode='markers',
                name='5-Yr Avg',
                marker=dict(size=7, color='white', symbol='diamond', line=dict(color='#000000', width=1.5)),
                showlegend=False,
                hovertemplate='5-Yr Avg: %{y:.2f}M MT<extra></extra>'
            ),
            row=2, col=1
        )

    # 5. Commitments vs USDA Target (Row 2, Col 2)
    if usda_estimate and not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns:
        estimate_mt = usda_estimate['estimate_mt'] / 1e6
        current_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6
        gap_to_target = estimate_mt - current_commitments

        target_categories = ['Current<br>Commitments', 'Additional Sales<br>Needed', 'USDA<br>Target']
        target_values = [current_commitments, max(0, gap_to_target), estimate_mt]
        target_colors = [BENDIGO_COLORS['secondary'], BENDIGO_COLORS['light1'], BENDIGO_COLORS['dark1']]

        # Create stacked bar showing commitments + gap
        fig.add_trace(
            go.Bar(
                name='Commitments',
                x=['Progress'],
                y=[current_commitments],
                marker_color=BENDIGO_COLORS['secondary'],
                text=f'<b>{current_commitments:.1f}M</b>',
                textposition='inside',
                textfont=dict(size=11, color='white'),
                hovertemplate=f'Commitments: {current_commitments:.2f}M MT<extra></extra>',
                showlegend=False
            ),
            row=2, col=2
        )

        if gap_to_target > 0:
            fig.add_trace(
                go.Bar(
                    name='Gap',
                    x=['Progress'],
                    y=[gap_to_target],
                    marker_color=BENDIGO_COLORS['light1'],
                    text=f'{gap_to_target:.1f}M<br>needed',
                    textposition='inside',
                    hovertemplate=f'Additional needed: {gap_to_target:.2f}M MT<extra></extra>',
                    showlegend=False
                ),
                row=2, col=2
            )

        # Add target threshold line
        fig.add_shape(
            type='line',
            x0=-0.5, x1=0.5,
            y0=estimate_mt, y1=estimate_mt,
            line=dict(color='#1F2937', width=2, dash='solid'),
            row=2, col=2
        )

        # Add target marker with arrow
        fig.add_trace(
            go.Scatter(
                x=['Progress'],
                y=[estimate_mt],
                mode='markers+text',
                marker=dict(size=12, color=BENDIGO_COLORS['dark1'], symbol='triangle-down'),
                text=f'↓ {estimate_mt:.1f}M',
                textposition='top center',
                textfont=dict(size=10, color=BENDIGO_COLORS['dark1']),
                hovertemplate=f'USDA Target: {estimate_mt:.2f}M MT<extra></extra>',
                showlegend=False
            ),
            row=2, col=2
        )
    
    # Narrative header calculation
    narrative_headline = "US Wheat Exports — "
    if not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns and usda_estimate:
        current_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6
        estimate_mt = usda_estimate['estimate_mt'] / 1e6
        gap_remaining = estimate_mt - current_commitments
        commitments_pct = (current_commitments / estimate_mt) * 100
        narrative_headline += f"Strong Early Pace ({commitments_pct:.0f}% of Target), but {gap_remaining:.1f} MMT Gap Remains"
    else:
        narrative_headline += "Export Pace Analysis"

    # Update layout with narrative header and tighter spacing
    fig.update_layout(
        title={
            'text': f"<b>{narrative_headline}</b><br><sub style='font-size:10px; color:#6B7280'>MY 2026 • Week {current_weeks if current_weeks > 0 else '?'} • USDA Target: 24.5 MMT</sub>",
            'x': 0.02,
            'xanchor': 'left',
            'font': {'size': 15, 'color': BENDIGO_COLORS['foreground'], 'family': 'Arial'}
        },
        height=850,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=0.46,          # Position below the pace chart (top row)
            xanchor="left",
            x=0.02,          # Align with left edge of pace chart
            font=dict(size=10),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#D1D5DB',
            borderwidth=0.5
        ),
        plot_bgcolor=BENDIGO_COLORS['background'],
        paper_bgcolor=BENDIGO_COLORS['background'],
        barmode='stack',
        margin=dict(l=60, r=40, t=100, b=80)
    )

    # Update axis labels and formatting
    # Row 1: Full Season Pace + Sales Pipeline
    fig.update_xaxes(title_text="Marketing Week", row=1, col=1, range=[0, 53])
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=1, col=1)
    fig.update_xaxes(title_text="", row=1, col=2)
    fig.update_yaxes(title_text="Million MT", row=1, col=2)

    # Row 2: Latest Week Comparison + Commitments vs Target
    fig.update_xaxes(
        title_text="Wheat Class",
        row=2, col=1,
        tickangle=0,
        tickfont=dict(size=13, color=BENDIGO_COLORS['foreground'], family='Arial Black')
    )
    fig.update_yaxes(title_text="Cumulative Exports (Million MT)", row=2, col=1)
    fig.update_xaxes(title_text="", row=2, col=2)
    fig.update_yaxes(title_text="Million MT", row=2, col=2)

    # Add McKinsey-style callout annotations
    annotations = []

    if usda_estimate and 107 in summary_data and historical_stats:
        estimate_mt = usda_estimate['estimate_mt'] / 1e6
        current_val = summary_data[107]['latest']
        current_weeks = summary_data[107]['weeks']

        # NOTE: projected_final is set to USDA estimate at line 335 (simple approach)
        # Complex projection modeling on backburner

        # Get historical context
        if current_weeks in historical_stats:
            avg_at_week = historical_stats[current_weeks]['avg'] / 1e6
            pct_vs_avg = ((current_val / avg_at_week) - 1) * 100

            # Callout 1: Current performance - simplified (2 lines max)
            annotations.append(dict(
                xref='x', yref='y',
                x=4, y=23,
                text=f"<b>Wk {current_weeks}: {current_val:.1f}M MT</b><br>+{pct_vs_avg:.0f}% vs 5-yr avg ({avg_at_week:.1f}M)",
                showarrow=False,
                font=dict(size=8.5, color=BENDIGO_COLORS['foreground']),
                align='left',
                bgcolor='#FAFAFA',
                bordercolor='#D1D5DB',
                borderwidth=0.75,
                borderpad=4,
                xanchor='left',
                yanchor='top'
            ))

        # Callout 2: Commitments - simplified (2 lines max)
        if not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns:
            current_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6
            commitments_pct_of_target = (current_commitments / estimate_mt) * 100

            annotations.append(dict(
                xref='x', yref='y',
                x=18, y=19,
                text=f"<b>Commits: {current_commitments:.1f}M MT</b><br>{commitments_pct_of_target:.0f}% of USDA target",
                showarrow=False,
                font=dict(size=8.5, color=BENDIGO_COLORS['foreground']),
                align='left',
                bgcolor='#FAFAFA',
                bordercolor='#D1D5DB',
                borderwidth=0.75,
                borderpad=4,
                xanchor='left',
                yanchor='top'
            ))

        # Callout 3: GAP - Prominent box (this is the key message)
        if not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns:
            current_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6
            gap_remaining = estimate_mt - current_commitments
            weeks_left = 53 - current_weeks
            sales_per_week = gap_remaining / weeks_left if weeks_left > 0 else 0

            gap_text = f"<b>GAP: {gap_remaining:.1f} MMT</b><br>Need {sales_per_week:.2f}M MT/wk × {weeks_left} wks"

            annotations.append(dict(
                xref='x', yref='y',
                x=42, y=8,
                text=gap_text,
                showarrow=False,
                font=dict(size=9.5, color='#FFFFFF', family='Arial Black'),
                align='center',
                bgcolor=BENDIGO_COLORS['secondary'],
                bordercolor=BENDIGO_COLORS['dark1'],
                borderwidth=2.5,
                borderpad=8,
                xanchor='center',
                yanchor='middle'
            ))

        # Callout 4: Key Takeaways Box (Executive Summary)
        if not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns and current_weeks in historical_stats:
            current_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6
            avg_at_week = historical_stats[current_weeks]['avg'] / 1e6
            pct_vs_avg = ((current_val / avg_at_week) - 1) * 100
            commitments_pct = (current_commitments / estimate_mt) * 100
            gap_remaining = estimate_mt - current_commitments
            weeks_left = 53 - current_weeks
            sales_per_week_needed = gap_remaining / weeks_left if weeks_left > 0 else 0

            takeaway_text = (
                f"<b>Key Takeaways</b><br>"
                f"• Shipments {abs(pct_vs_avg):.0f}% {'above' if pct_vs_avg > 0 else 'below'} 5-yr avg<br>"
                f"• Commitments at {commitments_pct:.0f}% of USDA target<br>"
                f"• Gap of {gap_remaining:.1f} MMT with {sales_per_week_needed:.2f} MMT/week needed<br>"
                f"• Pace must {'improve materially' if gap_remaining > 5 else 'continue steadily'} in Q3/Q4"
            )

            # Position in paper coordinates (works across all subplots)
            annotations.append(dict(
                xref='paper', yref='paper',
                x=0.01, y=0.02,
                text=takeaway_text,
                showarrow=False,
                font=dict(size=9, color=BENDIGO_COLORS['foreground'], family='Arial'),
                align='left',
                bgcolor='#F9FAFB',
                bordercolor=BENDIGO_COLORS['primary'],
                borderwidth=1.5,
                borderpad=8,
                xanchor='left',
                yanchor='bottom'
            ))

    # Apply annotations to the figure
    if annotations:
        fig.update_layout(annotations=annotations)
    
    # Save dashboard
    output_file = "output/enhanced_wheat_multi_commodity_comparison.html"
    fig.write_html(output_file)
    
    print(f"✅ Enhanced comparison dashboard saved to: {output_file}")
    
    # Summary
    print("\n📊 WHEAT EXPORT SUMMARY (MY 2026)")
    print("=" * 50)

    # Separate individual classes from All Wheat aggregate
    individual_commodities = [(c, d) for c, d in summary_data.items() if c != 107]
    individual_commodities.sort(key=lambda x: x[1]['latest'], reverse=True)

    total_individual = sum(data['latest'] for comm, data in individual_commodities)

    weeks_text = f"{summary_data[individual_commodities[0][0]]['weeks']} weeks" if individual_commodities else ""
    print(f"Individual Wheat Classes ({weeks_text}):")

    for commodity, data in individual_commodities:
        percentage = (data['latest'] / total_individual * 100) if total_individual > 0 else 0
        print(f"  • {data['name']:20} | {data['latest']:5.2f}M MT | {percentage:5.1f}%")

    print(f"  {'─' * 45}")
    print(f"  {'TOTAL INDIVIDUAL':20} | {total_individual:5.2f}M MT | 100.0%")

    if 107 in summary_data:
        all_wheat_data = summary_data[107]
        print(f"\nAll Wheat (aggregate, {all_wheat_data['weeks']} weeks):")
        print(f"  • Latest cumulative   | {all_wheat_data['latest']:5.2f}M MT")

    if not all_wheat_2025.empty:
        print(f"\nMY 2025 All Wheat (historical comparison):")
        print(f"  • Complete year (53 weeks) | {all_wheat_2025.accumulated_exports_mt.max()/1e6:5.2f}M MT")

    # Show 5-year context
    if historical_stats:
        # Get the latest week's stats
        latest_week = current_weeks if current_weeks > 0 else 0
        if latest_week in historical_stats:
            avg_at_week = historical_stats[latest_week]['avg'] / 1e6
            min_at_week = historical_stats[latest_week]['min'] / 1e6
            max_at_week = historical_stats[latest_week]['max'] / 1e6
            current_val = summary_data[107]['latest'] if 107 in summary_data else 0

            print(f"\n5-Year Historical Context (2020-2024) at Week {latest_week}:")
            print(f"  • Average:     {avg_at_week:5.2f}M MT")
            print(f"  • Range:       {min_at_week:5.2f}M - {max_at_week:5.2f}M MT")
            print(f"  • MY 2026:     {current_val:5.2f}M MT", end="")

            # Show where current year sits vs average
            if current_val > avg_at_week:
                pct_above = ((current_val / avg_at_week) - 1) * 100
                print(f" ({pct_above:+.1f}% vs avg)")
            elif current_val < avg_at_week:
                pct_below = ((current_val / avg_at_week) - 1) * 100
                print(f" ({pct_below:+.1f}% vs avg)")
            else:
                print(" (at avg)")

    # Show USDA estimate comparison
    if usda_estimate and 107 in summary_data:
        estimate_mt = usda_estimate['estimate_mt'] / 1e6
        current_val = summary_data[107]['latest']
        current_weeks = summary_data[107]['weeks']

        # Required pace to hit estimate
        required_at_week = estimate_mt * (current_weeks / 53)

        # NOTE: projected_final is set to USDA estimate (line 335) for simplicity
        # Complex projection modeling on backburner - using official USDA target as reference

        print(f"\nUSDA Export Estimate ({usda_estimate['wasde_report']}):")
        print(f"  • Full Season Target: {estimate_mt:5.2f}M MT")
        print(f"  • Required at Wk {current_weeks:2d}: {required_at_week:5.2f}M MT")
        print(f"  • Actual at Wk {current_weeks:2d}:   {current_val:5.2f}M MT", end="")

        # Show ahead/behind
        variance = current_val - required_at_week
        if variance > 0:
            pct_ahead = (variance / required_at_week) * 100
            print(f" ({variance:+.2f}M MT, {pct_ahead:+.1f}% ahead of pace)")
        elif variance < 0:
            pct_behind = (variance / required_at_week) * 100
            print(f" ({variance:+.2f}M MT, {pct_behind:.1f}% behind pace)")
        else:
            print(" (on pace)")

        # Gap to target
        gap_to_target = estimate_mt - current_val
        print(f"  • Gap to Target:      {gap_to_target:5.2f}M MT ({(gap_to_target/estimate_mt)*100:.1f}% remaining)")

    # Show commitments analysis
    if not all_wheat_2026.empty and 'total_commitment_mt' in all_wheat_2026.columns:
        current_exports = all_wheat_2026.accumulated_exports_mt.iloc[-1] / 1e6
        outstanding_sales = all_wheat_2026.outstanding_sales_mt.iloc[-1] / 1e6
        total_commitments = all_wheat_2026.total_commitment_mt.iloc[-1] / 1e6

        print(f"\n📋 SALES PIPELINE ANALYSIS (Week {current_weeks})")
        print("=" * 50)
        print(f"  • Shipped (Actual Exports):  {current_exports:5.2f}M MT")
        print(f"  • Outstanding Sales (Sold):  {outstanding_sales:5.2f}M MT")
        print(f"  {'─' * 48}")
        print(f"  • Total Commitments:         {total_commitments:5.2f}M MT")

        if usda_estimate:
            commitments_pct = (total_commitments / estimate_mt) * 100
            sales_gap = estimate_mt - total_commitments
            weeks_left = 53 - current_weeks
            sales_per_week_needed = sales_gap / weeks_left if weeks_left > 0 else 0

            print(f"\n  Commitments Status:")
            print(f"  • % of USDA target:          {commitments_pct:5.1f}%")
            print(f"  • Additional sales needed:   {sales_gap:5.2f}M MT")
            print(f"  • Weekly sales pace needed:  {sales_per_week_needed:5.2f}M MT/week")
            print(f"  • Weeks remaining:           {weeks_left} weeks")

    return output_file

if __name__ == "__main__":
    try:
        output_file = create_enhanced_comparison_dashboard()
        
        if output_file:
            print(f"\n🎉 Enhanced multi-commodity dashboard with commitments analysis created!")
            print(f"📂 Open: {output_file}")
            print("\n💡 This dashboard provides:")
            print("   • Full season pace analysis with commitments tracking")
            print("   • Sales pipeline breakdown (shipped vs outstanding)")
            print("   • Commitments vs USDA target progress")
            print("   • Individual wheat class breakdown and comparison")
            print("   • MY 2025 All Wheat historical reference")
            print("   • McKinsey-style insights and callouts")
            print(f"   • Beautiful Bendigo color theme 🎨")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()