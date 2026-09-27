import pandas as pd

from puntbot.experiments import _prepare
from puntbot.meeting_types import assign_slices, run_meeting_types, summarise_slice


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "meeting_date": ["2025-03-01"] * 4 + ["2026-03-01"] * 4,
            "win_market_id": [1, 1, 1, 1, 2, 2, 2, 2],
            "win_bsp": [3.0, 4.0, 5.0, 6.0] * 2,
            "win_preplay_volume": [500.0] * 8,
            "model_p": [0.25, 0.25, 0.25, 0.25] * 2,
            "won": [1, 0, 0, 0, 0, 0, 0, 1],
            "speed_discard": [0] * 8,
            "speed_rating": [1.0] * 8,
            "track_code": ["AP"] * 8,
            "race_type": ["Pace"] * 8,
            "metro_grade": [1.0] * 8,
            "metro_track": [1.0] * 8,
            "dist_band": [0.0] * 8,
        }
    )


def test_assign_slices_includes_predeclared_families():
    families = {family for family, _label, _mask in assign_slices(_frame())}
    assert {"gait", "grade", "venue", "distance", "track", "track_gait"} <= families


def test_summarise_slice_scores_the_whole_band():
    summary = summarise_slice(_prepare(_frame()), "all", "All")
    assert summary["band_n"] == 8
    assert summary["model_beats_bsp"] is False


def test_run_meeting_types_keeps_predeclared_labels_when_sample_is_large():
    big = pd.concat([_frame()] * 40, ignore_index=True)
    big["win_market_id"] = range(len(big))
    results = run_meeting_types(big)
    labels = set(results["slice"])
    assert "Pace" in labels
    assert "All holdout runners" in labels
