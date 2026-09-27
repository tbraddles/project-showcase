import pandas as pd

from puntbot.backtest import back_profit
from puntbot.experiments import _backs, _prepare, frozen_candidate_mask, lay_profit, run_experiments


def _minimal_predictions_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "won": [1, 0, 0],
            "win_market_id": [1, 1, 2],
            "win_bsp": [4.0, 6.0, 3.0],
            "model_p": [0.30, 0.20, 0.40],
            "win_preplay_volume": [500.0, 500.0, 500.0],
            "meeting_date": ["2024-10-01", "2024-10-01", "2024-10-02"],
            "speed_discard": [0, 1, 0],
            "speed_rating": [10.0, 9.0, 11.0],
            "speed_rank": [1, 2, 1],
        }
    )


def test_frozen_candidate_exists_as_back_with_one_dollar_stake():
    data = _prepare(_minimal_predictions_frame())
    mask = frozen_candidate_mask(data)
    summary = _backs(data, mask, "frozen_candidate")

    assert summary["strategy"] == "frozen_candidate"
    assert summary["bets"] == 2
    assert summary["profit"] == back_profit(True, 4.0, 1.0) + back_profit(False, 3.0, 1.0)
    assert summary["roi"] == summary["profit"] / summary["bets"]

    results = run_experiments(_minimal_predictions_frame())
    assert "frozen_candidate" in results["strategy"].values


def test_successful_lay_pays_the_odds_fraction_net_of_commission():
    # Risk $1 at 5.0: collect 1/4 * 0.94 if the horse loses.
    assert abs(lay_profit(False, 5.0, liability=1.0, commission=0.06) - 0.235) < 1e-9


def test_winning_horse_costs_one_unit_of_liability():
    assert lay_profit(True, 5.0, liability=1.0) == -1.0
