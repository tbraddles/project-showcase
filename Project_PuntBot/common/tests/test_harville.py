import numpy as np
import pandas as pd

from common.harville import harville_place_probs
from common.place import add_harville, build_place_report


def test_two_horse_race_both_place():
    probs = harville_place_probs(np.array([0.7, 0.3]), n_places=2)
    assert np.allclose(probs, [1.0, 1.0])


def test_equal_three_horse_top_two():
    probs = harville_place_probs(np.array([1 / 3, 1 / 3, 1 / 3]), n_places=2)
    assert np.allclose(probs, [2 / 3, 2 / 3, 2 / 3], atol=1e-9)


def test_place_report_runs_on_tiny_race():
    frame = pd.DataFrame(
        {
            "win_market_id": ["m"] * 3,
            "win_bsp": [2.0, 4.0, 4.0],
            "place_bsp": [1.3, 1.8, 1.8],
            "placed": [1, 1, 0],
        }
    )
    scored = add_harville(frame)
    assert scored["harville_p"].between(0, 1).all()
    text = build_place_report(frame, "harness")
    assert "Harville" in text
    assert "PLACE_BSP" in text
