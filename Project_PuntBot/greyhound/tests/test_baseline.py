import pandas as pd

from common.baseline import build_baseline_text
from common.betting import brier_score
from common.hub import parse_meeting_date


def test_parse_meeting_date_day_first_and_iso():
    parsed = parse_meeting_date(pd.Series(["15/01/2025", "2025-08-01"]))
    assert parsed.dt.strftime("%Y-%m-%d").tolist() == ["2025-01-15", "2025-08-01"]


def test_brier_perfect_is_zero():
    assert brier_score(pd.Series([1.0, 0.0]), pd.Series([1.0, 0.0])) == 0.0


def test_empty_baseline_mentions_greyhound():
    text = build_baseline_text(pd.DataFrame(), "greyhound")
    assert "greyhound" in text.lower()
