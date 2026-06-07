"""Marketing week calculation for US grain/oilseed marketing years."""
from datetime import date


# USDA marketing year start month by commodity code.
# Wheat (101-107, 201): June; Corn (401): September; Soybeans (801): September;
# Soy meal (901) / Soy oil (902): October.
MY_START_MONTH = {
    101: 6, 102: 6, 103: 6, 104: 6, 105: 6, 106: 6, 107: 6, 201: 6,
    401: 9,
    801: 9,
    901: 10,
    902: 10,
}


def my_start_month(commodity_code: int) -> int:
    return MY_START_MONTH.get(commodity_code, 6)


def marketing_week(market_year: int, week_ending: date, start_month: int = 6) -> int:
    """1-indexed marketing week within the given market_year.

    The marketing year starts on the 1st of `start_month` in (market_year - 1).
    week_ending is expected to be a Thursday (USDA ESR convention).
    """
    my_start = date(market_year - 1, start_month, 1)
    return (week_ending - my_start).days // 7 + 1
