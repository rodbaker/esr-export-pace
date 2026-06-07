"""Tests for centralized marketing-week / start-month logic."""
from datetime import date

import pandas as pd
import pytest

from src.esr_pace.marketing_week import (
    marketing_week, marketing_week_series, my_start_month,
)


def test_my_start_month_from_config():
    assert my_start_month(107) == 6    # All Wheat — June MY
    assert my_start_month(401) == 9    # Corn — September MY
    assert my_start_month(801) == 9    # Soybeans — September MY
    assert my_start_month(901) == 10   # Soybean Meal — October MY
    assert my_start_month(902) == 10   # Soybean Oil — October MY


def test_my_start_month_unknown_code_raises():
    with pytest.raises(ValueError, match="Unknown commodity code 999"):
        my_start_month(999)


def test_marketing_week_first_week_june_my():
    # MY2026 wheat starts 2025-06-01; first Thursday is 2025-06-05
    assert marketing_week(2026, date(2025, 6, 5), start_month=6) == 1


def test_marketing_week_first_week_september_my():
    # MY2026 corn starts 2025-09-01; week ending 2025-09-04 is week 1
    assert marketing_week(2026, date(2025, 9, 4), start_month=9) == 1


def test_marketing_week_rejects_pre_my_dates():
    with pytest.raises(ValueError, match="precedes"):
        marketing_week(2026, date(2025, 5, 28), start_month=6)


def test_marketing_week_series_matches_scalar():
    my = pd.Series([2026, 2026, 2026])
    we = pd.Series(['2025-06-05', '2025-06-12', '2026-05-28'])
    out = marketing_week_series(my, we, start_month=6)
    assert list(out) == [
        marketing_week(2026, date(2025, 6, 5), 6),
        marketing_week(2026, date(2025, 6, 12), 6),
        marketing_week(2026, date(2026, 5, 28), 6),
    ]


def test_marketing_week_series_rejects_pre_my_dates():
    with pytest.raises(ValueError, match="precedes"):
        marketing_week_series(
            pd.Series([2026]), pd.Series(['2025-05-28']), start_month=6)
