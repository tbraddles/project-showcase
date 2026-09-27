import pandas as pd

from puntbot.calibration import brier_score, build_report, expected_calibration_error, reliability_table


def test_brier_is_zero_when_perfect():
    won = pd.Series([1.0, 0.0, 1.0])
    assert brier_score(pd.Series([1.0, 0.0, 1.0]), won) == 0.0


def test_reliability_table_flags_overconfidence():
    # Model says ~0.37, horses win 20% — overconfident.
    prob = pd.Series([0.36, 0.37, 0.38, 0.39] * 5)
    won = pd.Series([1, 0, 0, 0] * 5)
    table = reliability_table(prob, won)
    row = table.loc[table["bin"] == "0.35-0.40"].iloc[0]
    assert row["actual"] < row["mean_p"]
    assert expected_calibration_error(prob, won) > 0


def test_build_report_includes_band_and_brier():
    frame = pd.DataFrame(
        {
            "meeting_date": ["2026-04-01"] * 4,
            "win_market_id": [1, 1, 1, 1],
            "win_bsp": [3.0, 4.0, 5.0, 6.0],
            "win_preplay_volume": [500.0] * 4,
            "model_p": [0.40, 0.30, 0.20, 0.10],
            "won": [1, 0, 0, 0],
            "speed_discard": [0, 0, 0, 0],
            "speed_rating": [1.0, 2.0, 3.0, 4.0],
            "track_code": ["AP"] * 4,
        }
    )
    text = build_report(frame)
    assert "Brier_model" in text
    assert "Brier_BSP" in text
    assert "$2.50-$8" in text or "2.50-8" in text
