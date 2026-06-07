"""Marketing week calculation for US grain/oilseed marketing years.

The marketing-year start month is configured per commodity in
config/commodities.yaml (my_start_month) — the single source of truth.
"""
from datetime import date

import numpy as np
import pandas as pd

from .config import config_manager


def my_start_month(commodity_code: int) -> int:
    """Marketing-year start month for a commodity, from commodities.yaml.

    Raises ValueError for codes not in the config — never silently defaults.
    """
    commodity = config_manager.get_commodity_by_code(commodity_code)
    if commodity is None:
        raise ValueError(
            f"Unknown commodity code {commodity_code}: add it "
            f"(with my_start_month) to config/commodities.yaml")
    return commodity.my_start_month


def marketing_week(market_year: int, week_ending: date, start_month: int = 6) -> int:
    """1-indexed marketing week within the given market_year.

    The marketing year starts on the 1st of `start_month` in (market_year - 1).
    week_ending is expected to be a Thursday (USDA ESR convention).
    Raises ValueError if week_ending precedes the marketing-year start.
    """
    my_start = date(market_year - 1, start_month, 1)
    week = (week_ending - my_start).days // 7 + 1
    if week < 1:
        raise ValueError(
            f"week_ending {week_ending} precedes MY{market_year} "
            f"start {my_start}")
    return week


def marketing_week_series(market_year: pd.Series, week_ending: pd.Series,
                          start_month: int) -> np.ndarray:
    """Vectorized marketing_week over two aligned Series.

    Returns a plain int ndarray (no index) so callers can assign it to any
    DataFrame regardless of index state. Same <1 guard as the scalar form.
    """
    we = pd.to_datetime(pd.Series(week_ending).reset_index(drop=True))
    my = pd.Series(market_year).reset_index(drop=True).astype(int)
    starts = pd.to_datetime(pd.DataFrame({
        'year': my - 1, 'month': start_month, 'day': 1,
    }))
    weeks = ((we - starts).dt.days // 7 + 1).astype(int)
    if (weeks < 1).any():
        bad = we[weeks < 1].min().date()
        raise ValueError(
            f"week_ending {bad} precedes marketing-year start "
            f"(month {start_month})")
    return weeks.to_numpy()
