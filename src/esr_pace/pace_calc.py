"""Calculate export pace metrics vs. historical averages."""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging
from dataclasses import dataclass
# from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
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

logger = logging.getLogger(__name__)


@dataclass
class PaceMetrics:
    """Container for pace analysis metrics."""
    marketing_week: int
    week_ending: str
    current_accumulated: float
    historical_avg_accumulated: float
    current_weekly: float
    historical_avg_weekly: float
    current_outstanding: float
    historical_avg_outstanding: float
    current_commitment: float
    historical_avg_commitment: float
    pace_deviation_mt: float
    pace_deviation_pct: float
    weekly_deviation_mt: float
    weekly_deviation_pct: float
    commitment_deviation_mt: float
    commitment_deviation_pct: float
    z_score_accumulated: Optional[float] = None
    z_score_weekly: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None


@dataclass
class StatisticalSummary:
    """Container for statistical analysis summary."""
    total_weeks_analyzed: int
    weeks_ahead_of_pace: int
    weeks_behind_pace: int
    avg_pace_deviation_pct: float
    max_positive_deviation_pct: float
    max_negative_deviation_pct: float
    current_pace_trend: str  # 'ahead', 'behind', 'on_pace'
    volatility_score: float
    outlier_weeks: List[int]
    seasonal_pattern_strength: float


class PaceAnalyzer:
    """Comprehensive export pace analysis system."""
    
    def __init__(self, db_path: str = "data/esr_data.db"):
        """Initialize the pace analyzer.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        # Analysis parameters
        self.historical_years = 5  # Number of years for baseline (improved from 3 to 5)
        # Performance thresholds aligned with domain expertise (.claude/agents/agricultural-domain-expert.md)
        self.normal_deviation_threshold = 10.0  # ±10% is on pace (normal)
        self.significant_deviation_threshold = 25.0  # ±10-25% is significant (changed from 20.0)
        self.major_deviation_threshold = 40.0  # ±25-40% is major, >40% is critical (changed from 30.0)
        
        logger.info(f"PaceAnalyzer initialized with database: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(str(self.db_path))
    
    def get_marketing_week_index(self, week_ending: str, market_year: int) -> int:
        """Calculate marketing week index (1-based) from week ending date.
        
        Marketing year starts June 1 of the previous calendar year.
        
        Args:
            week_ending: Week ending date (YYYY-MM-DD)
            market_year: Marketing year (e.g., 2026)
            
        Returns:
            Marketing week index (1-53 or 1-54)
        """
        # Marketing year starts June 1 of previous calendar year
        my_start = f"{market_year - 1}-06-01"
        
        # Calculate days difference and convert to weeks
        week_end_dt = pd.to_datetime(week_ending)
        my_start_dt = pd.to_datetime(my_start)
        
        days_diff = (week_end_dt - my_start_dt).days
        week_index = int(days_diff / 7) + 1
        
        return week_index
    
    def get_historical_baseline(self, commodity_code: int, 
                              end_market_year: Optional[int] = None) -> pd.DataFrame:
        """Calculate historical baseline averages by marketing week.
        
        Args:
            commodity_code: USDA commodity code (e.g., 107 for All Wheat)
            end_market_year: Last marketing year to include in baseline (exclusive)
                           If None, uses current max year - 1
        
        Returns:
            DataFrame with historical averages by marketing week index
        """
        # Use a fresh connection to avoid any state issues
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            # Determine the historical period
            if end_market_year is None:
                cursor = conn.execute(
                    "SELECT MAX(market_year) FROM fact_esr_world_weekly WHERE commodity_code = ?",
                    (commodity_code,)
                )
                max_year = cursor.fetchone()[0]
                end_market_year = max_year
            
            start_market_year = end_market_year - self.historical_years
            
            # Ensure we have sufficient data - check what years are actually available
            cursor = conn.execute(
                "SELECT MIN(market_year), MAX(market_year) FROM fact_esr_world_weekly WHERE commodity_code = ?",
                (commodity_code,)
            )
            min_year, max_year = cursor.fetchone()
            
            # Adjust if we don't have enough historical years
            if start_market_year < min_year:
                start_market_year = min_year
                logger.warning(f"Limited historical data available. Using years {start_market_year} to {end_market_year-1} instead of {self.historical_years} years")
            
            # Ensure we have at least 2 years for meaningful baseline
            if (end_market_year - start_market_year) < 2:
                raise ValueError(f"Insufficient historical data: only {end_market_year - start_market_year} years available, need at least 2")
            
            actual_years = end_market_year - start_market_year
            logger.info(f"Calculating {actual_years}-year baseline for commodity {commodity_code}: "
                       f"MY {start_market_year} to {end_market_year-1}")
            
            # Query historical data with marketing week calculation
            query = """
                SELECT 
                    commodity_code,
                    market_year,
                    week_ending,
                    weekly_exports_mt,
                    accumulated_exports_mt,
                    outstanding_sales_mt,
                    total_commitment_mt,
                    -- Calculate marketing week index (1-based, from June 1 of previous year)
                    CAST((julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1 AS INTEGER) as marketing_week_index
                FROM fact_esr_world_weekly
                WHERE commodity_code = ?
                  AND market_year >= ?
                  AND market_year < ?
                ORDER BY market_year, week_ending
            """
            
            logger.debug(f"Executing query with params: commodity_code={commodity_code}, start_year={start_market_year}, end_year={end_market_year}")
            logger.debug(f"Query text:\n{query}")
            
            # Simplified approach - just run the query directly
            logger.debug(f"Executing historical baseline query with params: {(commodity_code, start_market_year, end_market_year)}")
            
            df_historical = pd.read_sql_query(
                query, conn, 
                params=(commodity_code, start_market_year, end_market_year)
            )
            
            logger.debug(f"Query returned DataFrame with shape: {df_historical.shape}")
            logger.debug(f"DataFrame columns: {df_historical.columns.tolist() if not df_historical.empty else 'empty'}")
            
            if df_historical.empty:
                logger.error(f"Query returned empty result set for commodity {commodity_code}, "
                           f"years {start_market_year} to {end_market_year-1}")
                raise ValueError(f"No historical data found for commodity {commodity_code} "
                               f"in years {start_market_year}-{end_market_year-1}")
            
            # Calculate baseline averages and statistics by marketing week
            baseline = df_historical.groupby('marketing_week_index').agg({
                'weekly_exports_mt': ['mean', 'std', 'count'],
                'accumulated_exports_mt': ['mean', 'std', 'count'],
                'outstanding_sales_mt': ['mean', 'std', 'count'],
                'total_commitment_mt': ['mean', 'std', 'count']
            }).round(2)
            
            # Flatten column names
            baseline.columns = ['_'.join(col).strip() for col in baseline.columns]
            baseline = baseline.reset_index()
            
            # Add metadata
            baseline['baseline_years'] = actual_years  # Use actual years calculated, not the target
            baseline['target_baseline_years'] = self.historical_years  # Store the target for reference
            baseline['start_market_year'] = start_market_year
            baseline['end_market_year'] = end_market_year - 1
            baseline['commodity_code'] = commodity_code
            
            logger.info(f"Calculated baseline for {len(baseline)} marketing weeks")
            return baseline
            
        except Exception as e:
            logger.error(f"Failed to calculate historical baseline: {e}")
            raise
        finally:
            conn.close()
    
    def get_current_year_data(self, commodity_code: int, 
                            market_year: Optional[int] = None) -> pd.DataFrame:
        """Get current marketing year data with marketing week indices.
        
        Args:
            commodity_code: USDA commodity code
            market_year: Marketing year to analyze (if None, uses latest)
            
        Returns:
            DataFrame with current year data and marketing week indices
        """
        conn = self._get_connection()
        
        try:
            if market_year is None:
                # Get the latest marketing year
                cursor = conn.execute(
                    "SELECT MAX(market_year) FROM fact_esr_world_weekly WHERE commodity_code = ?",
                    (commodity_code,)
                )
                market_year = cursor.fetchone()[0]
            
            query = """
                SELECT 
                    commodity_code,
                    market_year,
                    week_ending,
                    weekly_exports_mt,
                    accumulated_exports_mt,
                    outstanding_sales_mt,
                    total_commitment_mt,
                    -- Calculate marketing week index (1-based, from June 1 of previous year)
                    CAST((julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1 AS INTEGER) as marketing_week_index
                FROM fact_esr_world_weekly
                WHERE commodity_code = ?
                  AND market_year = ?
                ORDER BY week_ending
            """
            
            df_current = pd.read_sql_query(
                query, conn,
                params=(commodity_code, market_year)
            )
            
            if df_current.empty:
                raise ValueError(f"No current year data found for commodity {commodity_code} MY {market_year}")
            
            logger.info(f"Retrieved {len(df_current)} weeks of current data for MY {market_year}")
            return df_current
            
        except Exception as e:
            logger.error(f"Failed to get current year data: {e}")
            raise
        finally:
            conn.close()
    
    def calculate_pace_deviations(self, commodity_code: int, 
                                market_year: Optional[int] = None) -> List[PaceMetrics]:
        """Calculate comprehensive pace deviations vs. historical baseline.
        
        Args:
            commodity_code: USDA commodity code
            market_year: Marketing year to analyze (if None, uses latest)
            
        Returns:
            List of PaceMetrics objects with detailed deviation analysis
        """
        # Get current year data and historical baseline
        df_current = self.get_current_year_data(commodity_code, market_year)
        current_year = int(df_current['market_year'].iloc[0])  # Ensure Python int, not numpy
        
        # For historical baseline, exclude the current year being analyzed
        df_baseline = self.get_historical_baseline(commodity_code, current_year)
        
        # Create baseline lookup dictionary
        baseline_lookup = df_baseline.set_index('marketing_week_index').to_dict('index')
        
        pace_metrics = []
        
        for _, row in df_current.iterrows():
            week_index = row['marketing_week_index']
            
            # Get historical averages for this marketing week
            baseline = baseline_lookup.get(week_index, {})
            
            if not baseline:
                logger.warning(f"No historical baseline found for marketing week {week_index}")
                continue
            
            # Extract baseline values
            hist_accumulated = baseline.get('accumulated_exports_mt_mean', 0)
            hist_weekly = baseline.get('weekly_exports_mt_mean', 0)
            hist_outstanding = baseline.get('outstanding_sales_mt_mean', 0)
            hist_commitment = baseline.get('total_commitment_mt_mean', 0)
            
            # Calculate deviations
            pace_dev_mt = row['accumulated_exports_mt'] - hist_accumulated
            pace_dev_pct = (pace_dev_mt / hist_accumulated * 100) if hist_accumulated > 0 else 0
            
            weekly_dev_mt = row['weekly_exports_mt'] - hist_weekly
            weekly_dev_pct = (weekly_dev_mt / hist_weekly * 100) if hist_weekly > 0 else 0
            
            commitment_dev_mt = row['total_commitment_mt'] - hist_commitment
            commitment_dev_pct = (commitment_dev_mt / hist_commitment * 100) if hist_commitment > 0 else 0
            
            # Calculate Z-scores for statistical significance
            accumulated_std = baseline.get('accumulated_exports_mt_std', 0)
            weekly_std = baseline.get('weekly_exports_mt_std', 0)
            
            z_score_accumulated = (pace_dev_mt / accumulated_std) if accumulated_std > 0 else None
            z_score_weekly = (weekly_dev_mt / weekly_std) if weekly_std > 0 else None
            
            # Calculate confidence intervals (95% CI) - simplified without scipy
            n_years = baseline.get('accumulated_exports_mt_count', 0)
            if accumulated_std > 0 and n_years > 1:
                # Use simplified 95% CI approximation (±2 std errors)
                margin_of_error = 2.0 * (accumulated_std / np.sqrt(n_years))
                ci_lower = hist_accumulated - margin_of_error
                ci_upper = hist_accumulated + margin_of_error
            else:
                ci_lower = ci_upper = None
            
            # Create PaceMetrics object
            metrics = PaceMetrics(
                marketing_week=week_index,
                week_ending=row['week_ending'],
                current_accumulated=row['accumulated_exports_mt'],
                historical_avg_accumulated=hist_accumulated,
                current_weekly=row['weekly_exports_mt'],
                historical_avg_weekly=hist_weekly,
                current_outstanding=row['outstanding_sales_mt'],
                historical_avg_outstanding=hist_outstanding,
                current_commitment=row['total_commitment_mt'],
                historical_avg_commitment=hist_commitment,
                pace_deviation_mt=pace_dev_mt,
                pace_deviation_pct=pace_dev_pct,
                weekly_deviation_mt=weekly_dev_mt,
                weekly_deviation_pct=weekly_dev_pct,
                commitment_deviation_mt=commitment_dev_mt,
                commitment_deviation_pct=commitment_dev_pct,
                z_score_accumulated=z_score_accumulated,
                z_score_weekly=z_score_weekly,
                confidence_interval_lower=ci_lower,
                confidence_interval_upper=ci_upper
            )
            
            pace_metrics.append(metrics)
        
        logger.info(f"Calculated pace deviations for {len(pace_metrics)} weeks")
        return pace_metrics
    
    def get_pace_summary(self, pace_metrics: List[PaceMetrics]) -> StatisticalSummary:
        """Generate statistical summary of pace analysis.
        
        Args:
            pace_metrics: List of PaceMetrics from calculate_pace_deviations
            
        Returns:
            StatisticalSummary with key insights
        """
        if not pace_metrics:
            raise ValueError("No pace metrics provided")
        
        # Extract deviation percentages
        deviations = [m.pace_deviation_pct for m in pace_metrics]
        weekly_deviations = [m.weekly_deviation_pct for m in pace_metrics]
        
        # Count weeks ahead/behind
        weeks_ahead = sum(1 for d in deviations if d > self.normal_deviation_threshold)
        weeks_behind = sum(1 for d in deviations if d < -self.normal_deviation_threshold)
        
        # Calculate current trend (last 4 weeks average)
        recent_weeks = min(4, len(deviations))
        recent_avg = np.mean(deviations[-recent_weeks:]) if recent_weeks > 0 else 0
        
        if recent_avg > self.normal_deviation_threshold:
            trend = "ahead"
        elif recent_avg < -self.normal_deviation_threshold:
            trend = "behind"
        else:
            trend = "on_pace"
        
        # Calculate volatility (coefficient of variation)
        volatility = np.std(deviations) / (abs(np.mean(deviations)) + 1e-6)  # Add small value to avoid division by zero
        
        # Identify outlier weeks (Z-score > 2)
        outliers = []
        for i, m in enumerate(pace_metrics):
            if m.z_score_accumulated is not None and abs(m.z_score_accumulated) > 2:
                outliers.append(m.marketing_week)
        
        # Calculate seasonal pattern strength using autocorrelation
        if len(deviations) > 12:  # Need sufficient data
            # Simple seasonal pattern detection
            seasonal_strength = abs(np.corrcoef(deviations[:-12], deviations[12:])[0, 1]) if len(deviations) > 24 else 0
        else:
            seasonal_strength = 0
        
        summary = StatisticalSummary(
            total_weeks_analyzed=len(pace_metrics),
            weeks_ahead_of_pace=weeks_ahead,
            weeks_behind_pace=weeks_behind,
            avg_pace_deviation_pct=np.mean(deviations),
            max_positive_deviation_pct=max(deviations) if deviations else 0,
            max_negative_deviation_pct=min(deviations) if deviations else 0,
            current_pace_trend=trend,
            volatility_score=volatility,
            outlier_weeks=outliers,
            seasonal_pattern_strength=seasonal_strength
        )
        
        return summary
    
    def classify_deviation_severity(self, deviation_pct: float) -> str:
        """Classify pace deviation severity based on agricultural thresholds.
        
        Args:
            deviation_pct: Pace deviation percentage
            
        Returns:
            Severity classification string
        """
        abs_dev = abs(deviation_pct)
        
        if abs_dev <= self.normal_deviation_threshold:
            return "normal"
        elif abs_dev <= self.significant_deviation_threshold:
            return "significant"
        elif abs_dev <= self.major_deviation_threshold:
            return "major"
        else:
            return "critical"
    
    def create_pace_chart(self, pace_metrics: List[PaceMetrics], 
                         title: str = "Export Pace Analysis") -> go.Figure:
        """Create comprehensive pace analysis chart.
        
        Args:
            pace_metrics: List of PaceMetrics from calculate_pace_deviations
            title: Chart title
            
        Returns:
            Plotly Figure object
        """
        if not pace_metrics:
            raise ValueError("No pace metrics provided")
        
        # Extract data for plotting
        weeks = [m.marketing_week for m in pace_metrics]
        dates = [pd.to_datetime(m.week_ending) for m in pace_metrics]
        current_accumulated = [m.current_accumulated / 1e6 for m in pace_metrics]  # Convert to millions MT
        historical_accumulated = [m.historical_avg_accumulated / 1e6 for m in pace_metrics]
        pace_deviations = [m.pace_deviation_pct for m in pace_metrics]
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=[
                'Accumulated Exports: Current vs Historical Average',
                'Export Pace Deviation (%)',
                'Weekly Export Volumes'
            ],
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}],
                   [{"secondary_y": False}], 
                   [{"secondary_y": False}]]
        )
        
        # Plot 1: Accumulated exports comparison
        fig.add_trace(
            go.Scatter(
                x=dates, y=current_accumulated,
                mode='lines+markers',
                name='Current Year',
                line=dict(color=BENDIGO_COLORS['primary'], width=3),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates, y=historical_accumulated,
                mode='lines+markers',
                name='5-Year Average',
                line=dict(color=BENDIGO_COLORS['secondary'], width=2, dash='dash'),
                marker=dict(size=5)
            ),
            row=1, col=1
        )
        
        # Add confidence intervals if available
        if pace_metrics[0].confidence_interval_lower is not None:
            ci_lower = [m.confidence_interval_lower / 1e6 for m in pace_metrics if m.confidence_interval_lower]
            ci_upper = [m.confidence_interval_upper / 1e6 for m in pace_metrics if m.confidence_interval_upper]
            
            if ci_lower and ci_upper:
                fig.add_trace(
                    go.Scatter(
                        x=dates, y=ci_upper,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, y=ci_lower,
                        mode='lines',
                        line=dict(width=0),
                        fill='tonexty',
                        fillcolor='rgba(222, 49, 59, 0.2)',
                        name='95% Confidence Interval',
                        hoverinfo='skip'
                    ),
                    row=1, col=1
                )
        
        # Plot 2: Pace deviation with threshold bands
        fig.add_trace(
            go.Scatter(
                x=dates, y=pace_deviations,
                mode='lines+markers',
                name='Pace Deviation',
                line=dict(color=BENDIGO_COLORS['dark1'], width=2),
                marker=dict(
                    size=8,
                    color=[self._get_deviation_color(d) for d in pace_deviations],
                    line=dict(width=1, color='white')
                )
            ),
            row=2, col=1
        )
        
        # Add threshold lines
        fig.add_hline(
            y=self.normal_deviation_threshold, 
            line_dash="dot", line_color=BENDIGO_COLORS['accent2'],
            annotation_text="Normal (+10%)",
            row=2, col=1
        )
        fig.add_hline(
            y=-self.normal_deviation_threshold, 
            line_dash="dot", line_color=BENDIGO_COLORS['accent2'],
            row=2, col=1
        )
        fig.add_hline(
            y=self.significant_deviation_threshold, 
            line_dash="dash", line_color=BENDIGO_COLORS['accent3'],
            annotation_text="Significant (+20%)",
            row=2, col=1
        )
        fig.add_hline(
            y=-self.significant_deviation_threshold, 
            line_dash="dash", line_color=BENDIGO_COLORS['accent3'],
            row=2, col=1
        )
        fig.add_hline(
            y=self.major_deviation_threshold, 
            line_dash="solid", line_color=BENDIGO_COLORS['secondary'],
            annotation_text="Major (+30%)",
            row=2, col=1
        )
        fig.add_hline(
            y=-self.major_deviation_threshold, 
            line_dash="solid", line_color=BENDIGO_COLORS['secondary'],
            row=2, col=1
        )
        
        # Plot 3: Weekly export volumes
        current_weekly = [m.current_weekly / 1e6 for m in pace_metrics]
        historical_weekly = [m.historical_avg_weekly / 1e6 for m in pace_metrics]
        
        fig.add_trace(
            go.Bar(
                x=dates, y=current_weekly,
                name='Current Weekly',
                marker=dict(color='rgba(135, 14, 64, 0.7)')
            ),
            row=3, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates, y=historical_weekly,
                mode='lines+markers',
                name='Historical Weekly Avg',
                line=dict(color=BENDIGO_COLORS['secondary'], width=2),
                marker=dict(size=5)
            ),
            row=3, col=1
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            height=900,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update y-axis labels
        fig['layout']['yaxis']['title'] = 'Accumulated Exports (Million MT)'
        fig['layout']['yaxis2']['title'] = 'Pace Deviation (%)'  
        fig['layout']['yaxis3']['title'] = 'Weekly Exports (Million MT)'
        
        # Update x-axis labels
        fig['layout']['xaxis3']['title'] = 'Week Ending Date'
        
        return fig
    
    def create_pace_dashboard(self, pace_metrics: List[PaceMetrics], 
                            summary: StatisticalSummary) -> go.Figure:
        """Create comprehensive dashboard with multiple pace visualizations.
        
        Args:
            pace_metrics: List of PaceMetrics from calculate_pace_deviations
            summary: StatisticalSummary from get_pace_summary
            
        Returns:
            Plotly Figure object with dashboard layout
        """
        if not pace_metrics:
            raise ValueError("No pace metrics provided")
        
        # Create subplots with custom grid
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Export Pace Trend',
                'Deviation Distribution', 
                'Weekly Performance Heatmap',
                'Key Performance Indicators'
            ],
            specs=[[{"type": "xy"}, {"type": "xy"}],
                   [{"type": "xy"}, {"type": "xy"}]],
            horizontal_spacing=0.1,
            vertical_spacing=0.15
        )
        
        # 1. Pace trend line with color coding
        dates = [pd.to_datetime(m.week_ending) for m in pace_metrics]
        pace_deviations = [m.pace_deviation_pct for m in pace_metrics]
        
        fig.add_trace(
            go.Scatter(
                x=dates, y=pace_deviations,
                mode='lines+markers',
                name='Pace Deviation',
                line=dict(color=BENDIGO_COLORS['foreground'], width=3),
                marker=dict(
                    size=10,
                    color=[self._get_deviation_color(d) for d in pace_deviations],
                    line=dict(width=2, color='white')
                ),
                hovertemplate='<b>Week %{x}</b><br>Deviation: %{y:.1f}%<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dot", line_color=BENDIGO_COLORS['light1'], row=1, col=1)
        
        # 2. Distribution histogram
        fig.add_trace(
            go.Histogram(
                x=pace_deviations,
                nbinsx=15,
                name='Deviation Distribution',
                marker=dict(
                    color='rgba(135, 14, 64, 0.7)',
                    line=dict(color='white', width=1)
                )
            ),
            row=1, col=2
        )
        
        # 3. Weekly performance heatmap data preparation
        weeks = [m.marketing_week for m in pace_metrics]
        weekly_deviations = [m.weekly_deviation_pct for m in pace_metrics]
        
        # Create heatmap matrix (simplified for visualization)
        heatmap_data = [[d] for d in weekly_deviations]
        heatmap_weeks = [f"Week {w}" for w in weeks]
        
        fig.add_trace(
            go.Heatmap(
                z=heatmap_data,
                y=heatmap_weeks,
                x=['Weekly Deviation %'],
                colorscale=[
                    [0, BENDIGO_COLORS['secondary']],     # Red for negative
                    [0.5, BENDIGO_COLORS['background']], # White for neutral  
                    [1, BENDIGO_COLORS['accent2']]       # Orange for positive
                ],
                zmid=0,
                showscale=True,
                hovertemplate='Week: %{y}<br>Deviation: %{z:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 4. KPI summary as text annotations
        kpi_text = f"""
        <b>Performance Summary</b><br>
        Total Weeks: {summary.total_weeks_analyzed}<br>
        Weeks Ahead: {summary.weeks_ahead_of_pace}<br>
        Weeks Behind: {summary.weeks_behind_pace}<br>
        <br>
        <b>Current Trend: {summary.current_pace_trend.upper()}</b><br>
        Avg Deviation: {summary.avg_pace_deviation_pct:.1f}%<br>
        Max Positive: +{summary.max_positive_deviation_pct:.1f}%<br>
        Max Negative: {summary.max_negative_deviation_pct:.1f}%<br>
        <br>
        Volatility Score: {summary.volatility_score:.2f}<br>
        Outlier Weeks: {len(summary.outlier_weeks)}
        """
        
        fig.add_annotation(
            text=kpi_text,
            xref="x domain", yref="y domain",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=12),
            bgcolor="rgba(226, 231, 233, 0.8)",
            bordercolor=BENDIGO_COLORS['light1'],
            borderwidth=1,
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f"Wheat Export Pace Dashboard - {summary.current_pace_trend.title()} of Historical Average",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            },
            height=700,
            showlegend=True,
            template="plotly_white"
        )
        
        # Update axes using layout dictionary approach
        fig['layout']['yaxis']['title'] = 'Pace Deviation (%)'
        fig['layout']['xaxis']['title'] = 'Week Ending Date'
        fig['layout']['xaxis2']['title'] = 'Pace Deviation (%)'
        fig['layout']['yaxis2']['title'] = 'Frequency'
        
        # Remove axes for KPI panel
        fig['layout']['xaxis4']['showticklabels'] = False
        fig['layout']['xaxis4']['showgrid'] = False
        fig['layout']['xaxis4']['zeroline'] = False
        fig['layout']['yaxis4']['showticklabels'] = False
        fig['layout']['yaxis4']['showgrid'] = False
        fig['layout']['yaxis4']['zeroline'] = False
        
        return fig
    
    def _get_deviation_color(self, deviation_pct: float) -> str:
        """Get color based on deviation severity using Bendigo theme.
        
        Args:
            deviation_pct: Pace deviation percentage
            
        Returns:
            Color string
        """
        severity = self.classify_deviation_severity(deviation_pct)
        
        if severity == "normal":
            return BENDIGO_COLORS['foreground']  # Dark gray for normal
        elif severity == "significant":
            return BENDIGO_COLORS['accent2']     # Orange for significant
        elif severity == "major":
            return BENDIGO_COLORS['secondary']   # Red for major
        else:  # critical
            return BENDIGO_COLORS['primary']     # Deep burgundy for critical
    
    def generate_pace_report(self, commodity_code: int, 
                           market_year: Optional[int] = None,
                           save_charts: bool = False,
                           output_dir: str = "output") -> Dict[str, Any]:
        """Generate comprehensive pace analysis report.
        
        Args:
            commodity_code: USDA commodity code
            market_year: Marketing year to analyze (if None, uses latest)
            save_charts: Whether to save chart files
            output_dir: Directory for output files
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        logger.info(f"Generating pace report for commodity {commodity_code}")
        
        # Calculate pace metrics
        pace_metrics = self.calculate_pace_deviations(commodity_code, market_year)
        summary = self.get_pace_summary(pace_metrics)
        
        # Get the actual market year analyzed
        analyzed_year = pace_metrics[0].week_ending[:4] if pace_metrics else str(market_year)
        
        # Create comprehensive report
        report = {
            'metadata': {
                'commodity_code': commodity_code,
                'market_year_analyzed': analyzed_year,
                'analysis_date': datetime.now().isoformat(),
                'weeks_analyzed': len(pace_metrics),
                'baseline_years': self.historical_years,
                'baseline_period': f"MY 2017-2026"  # Based on 10-year target data
            },
            'summary_statistics': {
                'total_weeks': summary.total_weeks_analyzed,
                'weeks_ahead_of_pace': summary.weeks_ahead_of_pace,
                'weeks_behind_pace': summary.weeks_behind_pace,
                'weeks_on_pace': summary.total_weeks_analyzed - summary.weeks_ahead_of_pace - summary.weeks_behind_pace,
                'current_trend': summary.current_pace_trend,
                'avg_deviation_pct': round(summary.avg_pace_deviation_pct, 2),
                'max_positive_deviation_pct': round(summary.max_positive_deviation_pct, 2),
                'max_negative_deviation_pct': round(summary.max_negative_deviation_pct, 2),
                'volatility_score': round(summary.volatility_score, 3),
                'outlier_weeks': summary.outlier_weeks,
                'seasonal_pattern_strength': round(summary.seasonal_pattern_strength, 3)
            },
            'current_status': self._generate_current_status(pace_metrics, summary),
            'key_insights': self._generate_key_insights(pace_metrics, summary),
            'recommendations': self._generate_recommendations(pace_metrics, summary),
            'detailed_metrics': [self._pace_metric_to_dict(m) for m in pace_metrics],
            'charts': {}
        }
        
        # Generate and optionally save charts
        if save_charts:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Main pace chart
            pace_chart = self.create_pace_chart(pace_metrics, 
                                              f"Wheat Export Pace Analysis - MY {analyzed_year}")
            pace_chart_file = output_path / f"pace_analysis_{commodity_code}_{analyzed_year}.html"
            pace_chart.write_html(str(pace_chart_file))
            report['charts']['pace_analysis'] = str(pace_chart_file)
            
            # Dashboard
            dashboard = self.create_pace_dashboard(pace_metrics, summary)
            dashboard_file = output_path / f"pace_dashboard_{commodity_code}_{analyzed_year}.html"
            dashboard.write_html(str(dashboard_file))
            report['charts']['dashboard'] = str(dashboard_file)
            
            logger.info(f"Charts saved to {output_path}")
        
        logger.info("Pace report generated successfully")
        return report
    
    def _generate_current_status(self, pace_metrics: List[PaceMetrics], 
                               summary: StatisticalSummary) -> Dict[str, Any]:
        """Generate current status analysis."""
        if not pace_metrics:
            return {}
        
        latest_metric = pace_metrics[-1]
        
        return {
            'latest_week_ending': latest_metric.week_ending,
            'marketing_week': latest_metric.marketing_week,
            'current_accumulated_exports_mt': latest_metric.current_accumulated,
            'historical_avg_accumulated_mt': latest_metric.historical_avg_accumulated,
            'pace_deviation_mt': latest_metric.pace_deviation_mt,
            'pace_deviation_pct': round(latest_metric.pace_deviation_pct, 2),
            'deviation_severity': self.classify_deviation_severity(latest_metric.pace_deviation_pct),
            'current_outstanding_sales_mt': latest_metric.current_outstanding,
            'current_total_commitment_mt': latest_metric.current_commitment,
            'weeks_ahead_vs_behind': {
                'ahead': summary.weeks_ahead_of_pace,
                'behind': summary.weeks_behind_pace,
                'ratio': summary.weeks_ahead_of_pace / max(summary.weeks_behind_pace, 1)
            }
        }
    
    def _generate_key_insights(self, pace_metrics: List[PaceMetrics], 
                             summary: StatisticalSummary) -> List[str]:
        """Generate key insights from the analysis."""
        insights = []
        
        if not pace_metrics:
            return ["Insufficient data for analysis"]
        
        # Current pace trend insight
        if summary.current_pace_trend == "ahead":
            insights.append(f"Current export pace is running ahead of the {self.historical_years}-year historical average by an average of {summary.avg_pace_deviation_pct:.1f}%")
        elif summary.current_pace_trend == "behind":
            insights.append(f"Current export pace is running behind the {self.historical_years}-year historical average by an average of {abs(summary.avg_pace_deviation_pct):.1f}%")
        else:
            insights.append(f"Current export pace is tracking closely with the {self.historical_years}-year historical average (±{abs(summary.avg_pace_deviation_pct):.1f}%)")
        
        # Volatility insight
        if summary.volatility_score > 1.0:
            insights.append(f"Export pace shows high volatility (score: {summary.volatility_score:.2f}), indicating inconsistent weekly performance")
        elif summary.volatility_score < 0.3:
            insights.append(f"Export pace shows low volatility (score: {summary.volatility_score:.2f}), indicating consistent performance")
        
        # Outlier weeks insight
        if summary.outlier_weeks:
            insights.append(f"Identified {len(summary.outlier_weeks)} statistical outlier weeks with extreme deviations: {summary.outlier_weeks}")
        
        # Performance distribution insight
        total_weeks = summary.total_weeks_analyzed
        if summary.weeks_ahead_of_pace > summary.weeks_behind_pace:
            insights.append(f"Predominantly ahead of pace: {summary.weeks_ahead_of_pace}/{total_weeks} weeks ahead vs {summary.weeks_behind_pace}/{total_weeks} weeks behind")
        elif summary.weeks_behind_pace > summary.weeks_ahead_of_pace:
            insights.append(f"Predominantly behind pace: {summary.weeks_behind_pace}/{total_weeks} weeks behind vs {summary.weeks_ahead_of_pace}/{total_weeks} weeks ahead")
        else:
            insights.append(f"Balanced performance: {summary.weeks_ahead_of_pace} weeks ahead, {summary.weeks_behind_pace} weeks behind")
        
        # Recent performance trend
        recent_metrics = pace_metrics[-4:]  # Last 4 weeks
        recent_avg = np.mean([m.pace_deviation_pct for m in recent_metrics])
        
        if len(recent_metrics) >= 4:
            if recent_avg > 15:
                insights.append(f"Recent 4-week performance strongly ahead of historical pace (+{recent_avg:.1f}% average)")
            elif recent_avg < -15:
                insights.append(f"Recent 4-week performance significantly behind historical pace ({recent_avg:.1f}% average)")
            else:
                insights.append(f"Recent 4-week performance aligned with historical pace ({recent_avg:.1f}% average)")
        
        return insights
    
    def _generate_recommendations(self, pace_metrics: List[PaceMetrics], 
                                summary: StatisticalSummary) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        if not pace_metrics:
            return ["Unable to generate recommendations - insufficient data"]
        
        latest_metric = pace_metrics[-1]
        deviation_severity = self.classify_deviation_severity(latest_metric.pace_deviation_pct)
        
        # Recommendations based on current deviation severity
        if deviation_severity == "critical":
            if latest_metric.pace_deviation_pct > 0:
                recommendations.extend([
                    "CRITICAL: Exports significantly exceed historical pace - investigate market factors driving exceptional demand",
                    "Monitor global wheat supply conditions and competitor export capacity",
                    "Assess domestic supply availability for sustained export levels"
                ])
            else:
                recommendations.extend([
                    "CRITICAL: Exports significantly below historical pace - urgent market assessment needed",
                    "Investigate competitive disadvantages or supply chain constraints",
                    "Consider policy interventions to improve export competitiveness"
                ])
        
        elif deviation_severity == "major":
            if latest_metric.pace_deviation_pct > 0:
                recommendations.extend([
                    "MAJOR: Strong export performance - verify supply chain capacity for sustained levels",
                    "Monitor domestic price impacts and farmer selling patterns"
                ])
            else:
                recommendations.extend([
                    "MAJOR: Weak export performance - analyze competitive position and pricing",
                    "Review trade policy impacts and market access issues"
                ])
        
        elif deviation_severity == "significant":
            recommendations.extend([
                "SIGNIFICANT: Export pace deviation warrants attention and monitoring",
                "Conduct detailed market analysis to understand underlying drivers"
            ])
        
        # Volatility-based recommendations
        if summary.volatility_score > 1.5:
            recommendations.append("HIGH VOLATILITY: Implement more frequent monitoring and consider stabilization measures")
        
        # Outstanding sales analysis
        if latest_metric.current_outstanding > latest_metric.historical_avg_outstanding * 1.2:
            recommendations.append("Strong forward sales position - monitor logistics capacity for timely shipments")
        elif latest_metric.current_outstanding < latest_metric.historical_avg_outstanding * 0.8:
            recommendations.append("Lower forward sales - enhance marketing efforts to capture future demand")
        
        # Trend-based recommendations
        if summary.current_pace_trend == "ahead":
            recommendations.append("Ahead of pace trend - ensure adequate supply chain capacity and monitor price impacts")
        elif summary.current_pace_trend == "behind":
            recommendations.append("Behind pace trend - evaluate competitive positioning and market access strategies")
        
        return recommendations
    
    def _pace_metric_to_dict(self, metric: PaceMetrics) -> Dict[str, Any]:
        """Convert PaceMetrics to dictionary for serialization."""
        return {
            'marketing_week': metric.marketing_week,
            'week_ending': metric.week_ending,
            'current_accumulated_mt': metric.current_accumulated,
            'historical_avg_accumulated_mt': metric.historical_avg_accumulated,
            'current_weekly_mt': metric.current_weekly,
            'historical_avg_weekly_mt': metric.historical_avg_weekly,
            'current_outstanding_mt': metric.current_outstanding,
            'historical_avg_outstanding_mt': metric.historical_avg_outstanding,
            'current_commitment_mt': metric.current_commitment,
            'historical_avg_commitment_mt': metric.historical_avg_commitment,
            'pace_deviation_mt': metric.pace_deviation_mt,
            'pace_deviation_pct': round(metric.pace_deviation_pct, 2),
            'weekly_deviation_mt': metric.weekly_deviation_mt,
            'weekly_deviation_pct': round(metric.weekly_deviation_pct, 2),
            'commitment_deviation_mt': metric.commitment_deviation_mt,
            'commitment_deviation_pct': round(metric.commitment_deviation_pct, 2),
            'z_score_accumulated': metric.z_score_accumulated,
            'z_score_weekly': metric.z_score_weekly,
            'confidence_interval_lower': metric.confidence_interval_lower,
            'confidence_interval_upper': metric.confidence_interval_upper,
            'deviation_severity': self.classify_deviation_severity(metric.pace_deviation_pct)
        }
    
    def export_report_to_json(self, report: Dict[str, Any], 
                            output_path: str) -> str:
        """Export comprehensive report to JSON file.
        
        Args:
            report: Report dictionary from generate_pace_report
            output_path: Path for output JSON file
            
        Returns:
            Path to created JSON file
        """
        import json
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert any numpy types to Python types for JSON serialization
        def convert_for_json(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Deep convert the report
        json_report = json.loads(json.dumps(report, default=convert_for_json))
        
        with open(output_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        logger.info(f"Report exported to {output_path}")
        return str(output_path)
    
    def print_executive_summary(self, report: Dict[str, Any]) -> None:
        """Print executive summary of the pace analysis.
        
        Args:
            report: Report dictionary from generate_pace_report
        """
        print("\n" + "="*60)
        print(" WHEAT EXPORT PACE ANALYSIS - EXECUTIVE SUMMARY")
        print("="*60)
        
        meta = report['metadata']
        stats = report['summary_statistics']
        status = report['current_status']
        
        print(f"\nANALYSIS OVERVIEW:")
        print(f"  Commodity: {meta['commodity_code']} (All Wheat)")
        print(f"  Marketing Year: {meta.get('market_year_analyzed', 'Current')}")
        print(f"  Weeks Analyzed: {meta['weeks_analyzed']}")
        print(f"  Baseline Period: {meta['baseline_period']}")
        print(f"  Analysis Date: {meta['analysis_date'][:10]}")
        
        print(f"\nCURRENT STATUS:")
        print(f"  Latest Week: {status['latest_week_ending']} (Marketing Week {status['marketing_week']})")
        print(f"  Pace Deviation: {status['pace_deviation_pct']:+.1f}% ({status['deviation_severity'].upper()})")
        print(f"  Current Trend: {stats['current_trend'].upper().replace('_', ' ')}")
        
        print(f"\nPERFORMANCE SUMMARY:")
        print(f"  Weeks Ahead of Pace: {stats['weeks_ahead_of_pace']}/{stats['total_weeks']}")
        print(f"  Weeks Behind Pace: {stats['weeks_behind_pace']}/{stats['total_weeks']}")
        print(f"  Average Deviation: {stats['avg_deviation_pct']:+.1f}%")
        print(f"  Volatility Score: {stats['volatility_score']:.2f}")
        
        if stats['outlier_weeks']:
            print(f"  Outlier Weeks: {len(stats['outlier_weeks'])} detected")
        
        print(f"\nKEY INSIGHTS:")
        for i, insight in enumerate(report['key_insights'], 1):
            print(f"  {i}. {insight}")
        
        print(f"\nRECOMMENDED ACTIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        print("\n" + "="*60)
    
    def create_historical_range_chart(self, commodity_code: int, 
                                    title: str = "Export Range Analysis") -> go.Figure:
        """Create historical range chart with current year overlay.
        
        Shows high/low range of cumulative exports over available years
        with current marketing year plotted as a line chart.
        
        Args:
            commodity_code: Commodity code to analyze
            title: Chart title
            
        Returns:
            Plotly Figure object
        """
        logger.info(f"Creating historical range chart for commodity {commodity_code}")
        
        with self._get_connection() as conn:
            # Get all available years except current year
            query_years = """
            SELECT DISTINCT market_year 
            FROM fact_esr_world_weekly 
            WHERE commodity_code = ? 
            ORDER BY market_year DESC
            """
            
            years_df = pd.read_sql_query(query_years, conn, params=(commodity_code,))
            all_years = years_df['market_year'].tolist()
            
            if len(all_years) < 2:
                raise ValueError(f"Insufficient data: only {len(all_years)} years available")
            
            current_year = max(all_years)
            historical_years = [y for y in all_years if y != current_year]
            
            logger.info(f"Historical years for range: {historical_years}")
            logger.info(f"Current year overlay: {current_year}")
            
            # Get historical data for range calculation
            historical_years_str = ','.join(map(str, historical_years))
            query_historical = f"""
            SELECT 
                marketing_week_index,
                market_year,
                accumulated_exports_mt,
                week_ending
            FROM (
                SELECT 
                    CAST((julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1 AS INTEGER) as marketing_week_index,
                    market_year,
                    SUM(weekly_exports_mt) OVER (
                        PARTITION BY market_year 
                        ORDER BY week_ending 
                        ROWS UNBOUNDED PRECEDING
                    ) as accumulated_exports_mt,
                    week_ending,
                    ROW_NUMBER() OVER (PARTITION BY market_year, week_ending ORDER BY week_ending) as rn
                FROM fact_esr_world_weekly 
                WHERE commodity_code = ? 
                AND market_year IN ({historical_years_str})
                AND weekly_exports_mt IS NOT NULL
            ) 
            WHERE rn = 1
            AND marketing_week_index BETWEEN 1 AND 53
            ORDER BY marketing_week_index, market_year
            """
            
            historical_df = pd.read_sql_query(query_historical, conn, params=(commodity_code,))
            
            # Get current year data
            query_current = """
            SELECT 
                marketing_week_index,
                accumulated_exports_mt,
                week_ending
            FROM (
                SELECT 
                    CAST((julianday(week_ending) - julianday((market_year - 1) || '-06-01')) / 7.0 + 1 AS INTEGER) as marketing_week_index,
                    SUM(weekly_exports_mt) OVER (
                        ORDER BY week_ending 
                        ROWS UNBOUNDED PRECEDING
                    ) as accumulated_exports_mt,
                    week_ending,
                    ROW_NUMBER() OVER (PARTITION BY week_ending ORDER BY week_ending) as rn
                FROM fact_esr_world_weekly 
                WHERE commodity_code = ? 
                AND market_year = ?
                AND weekly_exports_mt IS NOT NULL
            )
            WHERE rn = 1
            AND marketing_week_index BETWEEN 1 AND 53
            ORDER BY marketing_week_index
            """
            
            current_df = pd.read_sql_query(query_current, conn, params=(commodity_code, current_year))
            
        if historical_df.empty:
            raise ValueError("No historical data found")
        if current_df.empty:
            raise ValueError("No current year data found")
        
        # Calculate historical ranges by marketing week
        historical_ranges = historical_df.groupby('marketing_week_index')['accumulated_exports_mt'].agg([
            'min', 'max', 'mean', 'std'
        ]).reset_index()
        
        # Convert to millions of metric tons
        historical_ranges['min_mt'] = historical_ranges['min'] / 1e6
        historical_ranges['max_mt'] = historical_ranges['max'] / 1e6
        historical_ranges['mean_mt'] = historical_ranges['mean'] / 1e6
        
        current_df['accumulated_mt'] = current_df['accumulated_exports_mt'] / 1e6
        current_df['week_ending_date'] = pd.to_datetime(current_df['week_ending'])
        
        # Create the chart
        fig = go.Figure()
        
        # Add historical range band (high boundary - for hover only)
        fig.add_trace(
            go.Scatter(
                x=historical_ranges['marketing_week_index'], 
                y=historical_ranges['max_mt'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                name='Historical High Range',
                hovertemplate='<b>Marketing Week %{x}</b><br>' +
                              'Historical High Range: %{y:.2f}M MT<br>' +
                              '<extra></extra>'
            )
        )
        
        # Add low boundary with fill to high boundary - this shows as the range legend
        fig.add_trace(
            go.Scatter(
                x=historical_ranges['marketing_week_index'], 
                y=historical_ranges['min_mt'],
                mode='lines',
                line=dict(width=0),
                fill='tonexty',
                fillcolor='rgba(203, 204, 204, 0.3)',
                name=f'Historical High and Low Range ({min(historical_years)}-{max(historical_years)})',
                hovertemplate='<b>Marketing Week %{x}</b><br>' +
                              'Historical Low Range: %{y:.2f}M MT<br>' +
                              '<extra></extra>'
            )
        )
        
        # Add historical average line
        fig.add_trace(
            go.Scatter(
                x=historical_ranges['marketing_week_index'],
                y=historical_ranges['mean_mt'],
                mode='lines',
                line=dict(color=BENDIGO_COLORS['secondary'], width=2, dash='dash'),
                name=f'{len(historical_years)}-Year Average',
                hovertemplate='<b>Marketing Week %{x}</b><br>' +
                              'Historical Average: %{y:.2f}M MT<br>' +
                              '<extra></extra>'
            )
        )
        
        # Add current year line
        fig.add_trace(
            go.Scatter(
                x=current_df['marketing_week_index'],
                y=current_df['accumulated_mt'],
                mode='lines+markers',
                line=dict(color=BENDIGO_COLORS['primary'], width=3),
                marker=dict(size=6, color=BENDIGO_COLORS['primary']),
                name=f'MY {current_year} (Current)',
                hovertemplate='<b>Week %{x} (%{customdata})</b><br>' +
                              'Current Accumulated: %{y:.2f}M MT<br>' +
                              '<extra></extra>',
                customdata=current_df['week_ending']
            )
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f"{title}<br><sub>Marketing Year {current_year} vs {len(historical_years)}-Year Historical Range</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            },
            xaxis_title='Marketing Week',
            yaxis_title='Cumulative Exports (Million MT)',
            height=600,
            template='plotly_white',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # Add reference lines for key thresholds
        if not current_df.empty:
            current_max = current_df['accumulated_mt'].max()
            historical_max = historical_ranges['max_mt'].max()
            
            # Add annotation for current performance vs range
            latest_week = current_df['marketing_week_index'].iloc[-1]
            latest_current = current_df['accumulated_mt'].iloc[-1]
            
            # Find corresponding historical range for latest week
            historical_latest = historical_ranges[
                historical_ranges['marketing_week_index'] == latest_week
            ]
            
            if not historical_latest.empty:
                hist_min = historical_latest['min_mt'].iloc[0]
                hist_max = historical_latest['max_mt'].iloc[0]
                hist_mean = historical_latest['mean_mt'].iloc[0]
                
                # Determine position relative to range
                if latest_current > hist_max:
                    position_text = f"Above historical range (+{((latest_current/hist_max - 1)*100):.1f}%)"
                    position_color = BENDIGO_COLORS['secondary']
                elif latest_current < hist_min:
                    position_text = f"Below historical range ({((latest_current/hist_min - 1)*100):.1f}%)"
                    position_color = BENDIGO_COLORS['secondary']
                else:
                    position_text = f"Within historical range ({((latest_current/hist_mean - 1)*100):+.1f}% vs avg)"
                    position_color = BENDIGO_COLORS['accent2']
                
                fig.add_annotation(
                    x=latest_week,
                    y=latest_current,
                    text=position_text,
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=position_color,
                    ax=50,
                    ay=-50,
                    font=dict(color=position_color, size=12),
                    bordercolor=position_color,
                    borderwidth=1,
                    bgcolor="white"
                )
        
        return fig