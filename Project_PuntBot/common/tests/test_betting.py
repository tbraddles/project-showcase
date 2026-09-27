import pandas as pd

from common.betting import back_profit, brier_score, lay_profit
from common.hub import parse_meeting_date


def test_losing_back_loses_the_stake():
    assert back_profit(False, 3.0, stake=1.0) == -1.0


def test_lay_is_unit_liability():
    assert lay_profit(True, 16.0, liability=1.0) == -1.0


def test_parse_slash_dates_are_day_first():
    parsed = parse_meeting_date(pd.Series(["1/07/2025"]))
    assert parsed.dt.strftime("%Y-%m-%d").iloc[0] == "2025-07-01"


def test_brier_worse_when_wrong():
    assert brier_score([0.9], [0.0]) > brier_score([0.1], [0.0])
