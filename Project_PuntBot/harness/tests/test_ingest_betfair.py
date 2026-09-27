import pandas as pd

from puntbot.ingest_betfair import parse_meeting_date


def test_parse_meeting_date_accepts_iso_and_day_first_slashes():
    parsed = parse_meeting_date(pd.Series(["2025-08-01", "1/07/2025", "15/01/2025", ""]))
    assert parsed.dt.strftime("%Y-%m-%d").tolist()[:3] == ["2025-08-01", "2025-07-01", "2025-01-15"]
    assert pd.isna(parsed.iloc[3])
