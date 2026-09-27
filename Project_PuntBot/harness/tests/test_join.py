import pandas as pd

from puntbot.join import match_runners


def test_tab_number_match_beats_name():
    form = pd.DataFrame(
        [
            {
                "race_id": 1,
                "meeting_date": "2025-07-25",
                "track_code": "GP",
                "race_number": 1,
                "horse_name": "Flying Colours",
                "tab_number": 2,
                "place": 1,
            }
        ]
    )
    betfair = pd.DataFrame(
        [
            {
                "meeting_date": "2025-07-25",
                "track": "Gloucester Park",
                "race_no": 1,
                "tab_number": 2,
                "selection_name": "Some Other Name",
                "win_market_id": "1",
                "selection_id": "10",
            }
        ]
    )
    matches, stats = match_runners(form, betfair)
    assert stats["exact_tab"] == 1
    assert matches.iloc[0]["selection_id"] == "10"


def test_normalized_name_fallback():
    form = pd.DataFrame(
        [
            {
                "race_id": 2,
                "meeting_date": "2025-07-25",
                "track_code": "GP",
                "race_number": 1,
                "horse_name": "Flying Colours NZ",
                "tab_number": None,
                "place": 3,
            }
        ]
    )
    betfair = pd.DataFrame(
        [
            {
                "meeting_date": "2025-07-25",
                "track": "Gloucester Park",
                "race_no": 1,
                "tab_number": 4,
                "selection_name": "Flying Colours",
                "win_market_id": "2",
                "selection_id": "20",
            }
        ]
    )
    matches, stats = match_runners(form, betfair)
    assert stats["normalized_name"] == 1
    assert matches.iloc[0]["match_method"] == "normalized_name"
