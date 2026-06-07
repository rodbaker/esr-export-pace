#!/usr/bin/env python3
"""Multi-commodity grains export pace dashboard.

Covers wheat (HRW/SRW/HRS/White/Durum/All Wheat), Corn, Soybeans, Soybean Meal,
and Soybean Oil. Shows current MY pace vs the 5-year average envelope and the
top destination countries pulled from fact_esr_country_weekly.

Stays additive — does not modify enhanced_wheat_comparison.py.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_PATH = Path(__file__).parent / 'data' / 'esr_data.db'
OUTPUT_HTML = Path(__file__).parent / 'output' / 'enhanced_grains_comparison.html'

# Commodities and their friendly labels
GRAINS: List[Tuple[int, str, str]] = [
    (107, 'All Wheat', 'wheat'),
    (101, 'Wheat HRW', 'wheat'),
    (102, 'Wheat SRW', 'wheat'),
    (103, 'Wheat HRS', 'wheat'),
    (104, 'Wheat White', 'wheat'),
    (105, 'Wheat Durum', 'wheat'),
    (401, 'Corn', 'corn'),
    (801, 'Soybeans', 'soy'),
    (901, 'Soybean Meal', 'soy'),
    (902, 'Soybean Oil', 'soy'),
]

GROUP_COLORS = {
    'wheat': '#870E40',
    'corn': '#F37021',
    'soy':   '#1F6E3B',
}

def load_world_history(conn: sqlite3.Connection, code: int) -> pd.DataFrame:
    df = pd.read_sql_query(
        """SELECT market_year, week_ending, accumulated_exports_mt,
                  weekly_exports_mt, outstanding_sales_mt, total_commitment_mt
           FROM fact_esr_world_weekly
           WHERE commodity_code = ?
           ORDER BY market_year, week_ending""",
        conn, params=(code,),
    )
    if df.empty:
        return df
    df['week_ending'] = pd.to_datetime(df['week_ending'])
    # Ordinal week-within-season: position of the week in its MY, immune to
    # which weekday the MY start lands on (matches enhanced_wheat_comparison's
    # ROW_NUMBER alignment).
    df = df.sort_values(['market_year', 'week_ending']).reset_index(drop=True)
    df['mw'] = df.groupby('market_year').cumcount() + 1
    return df


def load_top_countries(conn: sqlite3.Connection, code: int, my: int,
                       top_n: int = 10) -> pd.DataFrame:
    q = """
    SELECT f.country_code,
           COALESCE(c.country_name, CAST(f.country_code AS TEXT)) AS country_name,
           MAX(f.accumulated_exports_mt) AS accumulated_mt,
           MAX(f.total_commitment_mt) AS commitment_mt
    FROM fact_esr_country_weekly f
    LEFT JOIN dim_country c ON c.country_code = f.country_code
    WHERE f.commodity_code = ? AND f.market_year = ?
    GROUP BY f.country_code, c.country_name
    ORDER BY accumulated_mt DESC
    LIMIT ?
    """
    df = pd.read_sql_query(q, conn, params=(code, my, top_n))
    df['country_name'] = df['country_name'].str.strip()
    return df


def pace_metric(hist: pd.DataFrame, current_my: int) -> Dict[str, float]:
    """Compare current-MY accumulated exports at the latest week vs the
    5-year average at the same ordinal week. pace_pct is None (not 0.0)
    when no baseline week exists."""
    cur = hist[hist['market_year'] == current_my]
    if cur.empty:
        return {'current_mt': 0.0, 'avg_mt': 0.0, 'pace_pct': None,
                'commitment_mt': 0.0, 'latest_week': ''}
    last = cur.sort_values('week_ending').iloc[-1]
    mw_now = int(last['mw'])
    five_year = hist[
        (hist['market_year'].between(current_my - 5, current_my - 1)) &
        (hist['mw'] == mw_now)
    ]
    avg = float(five_year['accumulated_exports_mt'].mean()) if not five_year.empty else None
    cur_acc = float(last['accumulated_exports_mt'])
    pace = ((cur_acc / avg) - 1) * 100 if avg else None
    return {
        'current_mt': cur_acc,
        'avg_mt': avg if avg is not None else 0.0,
        'pace_pct': pace,
        'commitment_mt': float(last['total_commitment_mt']),
        'latest_week': last['week_ending'].strftime('%Y-%m-%d'),
    }


def build_pace_figure(hist: pd.DataFrame, current_my: int, label: str,
                      color: str) -> go.Figure:
    fig = go.Figure()
    if hist.empty:
        fig.update_layout(title=f"{label} — no data")
        return fig

    # 5-year envelope (min/max) and average by ordinal week index
    past = hist[hist['market_year'].between(current_my - 5, current_my - 1)]
    if not past.empty:
        grp = past.groupby('mw')['accumulated_exports_mt']
        env = grp.agg(['min', 'max', 'mean']).reset_index().sort_values('mw')
        env['min_mmt'] = env['min'] / 1e6
        env['max_mmt'] = env['max'] / 1e6
        env['mean_mmt'] = env['mean'] / 1e6
        fig.add_trace(go.Scatter(
            x=list(env['mw']) + list(env['mw'])[::-1],
            y=list(env['max_mmt']) + list(env['min_mmt'])[::-1],
            fill='toself', fillcolor='rgba(180,180,180,0.25)',
            line=dict(color='rgba(255,255,255,0)'),
            name='5-yr min/max', hoverinfo='skip',
        ))
        fig.add_trace(go.Scatter(
            x=env['mw'], y=env['mean_mmt'],
            mode='lines', line=dict(color='#555555', dash='dash', width=2),
            name='5-yr average',
        ))

    # Prior individual seasons (faint)
    for my in sorted(hist['market_year'].unique()):
        if my == current_my or my < current_my - 5:
            continue
        season = hist[hist['market_year'] == my].sort_values('mw')
        fig.add_trace(go.Scatter(
            x=season['mw'], y=season['accumulated_exports_mt'] / 1e6,
            mode='lines', line=dict(color='rgba(120,120,120,0.45)', width=1),
            name=f'MY {my}', showlegend=False,
        ))

    # Current MY
    cur = hist[hist['market_year'] == current_my].sort_values('mw')
    if not cur.empty:
        fig.add_trace(go.Scatter(
            x=cur['mw'], y=cur['accumulated_exports_mt'] / 1e6,
            mode='lines+markers',
            line=dict(color=color, width=3),
            marker=dict(size=4, color=color),
            name=f'MY {current_my} (current)',
        ))

    fig.update_layout(
        title=f'{label} — Accumulated Exports vs 5-yr History',
        xaxis_title='Marketing week',
        yaxis_title='Accumulated exports (MMT)',
        template='plotly_white',
        height=380,
        margin=dict(l=50, r=30, t=60, b=50),
        legend=dict(orientation='h', y=-0.18),
    )
    return fig


def build_destinations_figure(top: pd.DataFrame, current_my: int, label: str,
                              color: str) -> go.Figure:
    fig = go.Figure()
    if top.empty:
        fig.update_layout(title=f"{label} destinations — no data")
        return fig
    top = top.iloc[::-1]  # horizontal: largest on top
    fig.add_trace(go.Bar(
        x=top['commitment_mt'] / 1e6,
        y=top['country_name'],
        orientation='h',
        marker_color=color,
        name='Total commitments',
        hovertemplate='%{y}: %{x:.2f} MMT<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=top['accumulated_mt'] / 1e6,
        y=top['country_name'],
        orientation='h',
        marker_color='rgba(0,0,0,0.55)',
        name='Shipped',
        hovertemplate='%{y}: %{x:.2f} MMT shipped<extra></extra>',
    ))
    fig.update_layout(
        title=f'{label} — Top 10 destinations (MY {current_my})',
        barmode='overlay',
        template='plotly_white',
        height=380,
        margin=dict(l=120, r=30, t=60, b=50),
        xaxis_title='MMT',
        legend=dict(orientation='h', y=-0.18),
    )
    return fig


def build_summary_table(rows: List[Dict]) -> str:
    """Render a small HTML table summarising the pace metric per commodity."""
    headers = ['Commodity', 'Latest Week', 'Accumulated (MMT)',
               '5-yr Avg (MMT)', 'Pace vs 5y', 'Total Commitments (MMT)']
    body = []
    for r in rows:
        pace = r['pace_pct']
        if pace is None:
            pace_cell = "<td class='pace-na'>n/a</td>"
            avg_cell = "<td>n/a</td>"
        else:
            cls = 'pace-up' if pace >= 0 else 'pace-dn'
            pace_cell = f"<td class='{cls}'>{pace:+.1f}%</td>"
            avg_cell = f"<td>{r['avg_mt']/1e6:,.2f}</td>"
        body.append(
            f"<tr><td>{r['label']}</td>"
            f"<td>{r['latest_week']}</td>"
            f"<td>{r['current_mt']/1e6:,.2f}</td>"
            f"{avg_cell}"
            f"{pace_cell}"
            f"<td>{r['commitment_mt']/1e6:,.2f}</td></tr>"
        )
    return (
        "<table class='summary'><thead><tr>"
        + ''.join(f'<th>{h}</th>' for h in headers)
        + "</tr></thead><tbody>"
        + ''.join(body)
        + "</tbody></table>"
    )


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    sections = []
    summary_rows: List[Dict] = []

    for code, label, group in GRAINS:
        hist = load_world_history(conn, code)
        if hist.empty:
            continue
        current_my = int(hist['market_year'].max())
        top = load_top_countries(conn, code, current_my)
        color = GROUP_COLORS[group]
        metric = pace_metric(hist, current_my)
        metric.update({'label': f'{label} (MY {current_my})', 'code': code})
        summary_rows.append(metric)

        pace_fig = build_pace_figure(hist, current_my, label, color)
        dest_fig = build_destinations_figure(top, current_my, label, color)

        sections.append(
            f"<section><h2>{label} <small>(code {code})</small></h2>"
            f"<div class='row'>"
            f"<div class='col'>{pace_fig.to_html(full_html=False, include_plotlyjs=False)}</div>"
            f"<div class='col'>{dest_fig.to_html(full_html=False, include_plotlyjs=False)}</div>"
            f"</div></section>"
        )

    conn.close()

    style = """
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
             margin: 30px; color: #323D42; background: #FAFAFA; }
      h1 { color: #870E40; margin-bottom: 4px; }
      h2 { color: #870E40; border-bottom: 2px solid #DE313B; padding-bottom: 6px;
           margin-top: 36px; }
      h2 small { color: #999; font-weight: normal; font-size: 0.7em; }
      .row { display: flex; gap: 18px; flex-wrap: wrap; }
      .col { flex: 1 1 480px; background: white; border-radius: 8px;
             box-shadow: 0 1px 4px rgba(0,0,0,0.08); padding: 8px; }
      .summary { border-collapse: collapse; margin-top: 18px; width: 100%;
                 background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
      .summary th, .summary td { padding: 8px 12px; border-bottom: 1px solid #eee;
                                 text-align: right; }
      .summary th { background: #870E40; color: white; text-align: center; }
      .summary td:first-child { text-align: left; font-weight: 600; }
      .pace-up { color: #15803d; font-weight: 600; }
      .pace-dn { color: #b91c1c; font-weight: 600; }
      .pace-na { color: #888; font-weight: 600; }
      .meta { color: #666; font-size: 0.9em; }
    </style>
    """
    summary_html = build_summary_table(summary_rows)
    generated = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'>
<title>US Grains Export Pace</title>
{style}
<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>
</head><body>
<h1>US Grains Export Pace</h1>
<div class='meta'>generated {generated} &middot; data source: USDA ESR</div>
<h2 style='margin-top:18px;border:0;'>Summary — pace vs 5-year average</h2>
{summary_html}
{''.join(sections)}
</body></html>"""

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding='utf-8')
    print(f"Wrote {OUTPUT_HTML}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
