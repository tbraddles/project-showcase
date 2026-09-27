import pandas as pd

from common.flow import build_flow_report, classify_move


def test_classify_move_come_in_and_drift():
    preplay = pd.Series([4.2, 3.0, 3.1])
    bsp = pd.Series([3.5, 3.6, 3.1])
    move = classify_move(preplay, bsp)
    assert move.tolist() == ["came_in", "drifted", "stable"]


def test_flow_report_names_the_buckets():
    frame = pd.DataFrame(
        {
            "win_preplay_ltp": [4.5, 3.0, 3.2],
            "win_bsp": [3.5, 3.8, 3.2],
            "won": [1, 0, 0],
            "win_preplay_volume": [300, 300, 300],
        }
    )
    text = build_flow_report(frame)
    assert "came in" in text
    assert "drifted" in text
