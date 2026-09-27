import pandas as pd

from puntbot.frozen_book import equity_curve, max_drawdown, select_frozen_bets, write_frozen_book


def _synthetic_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "won": [1, 0, 0, 1],
            "win_market_id": [1, 1, 2, 3],
            "win_bsp": [4.0, 6.0, 3.0, 5.0],
            "model_p": [0.35, 0.20, 0.40, 0.30],
            "win_preplay_volume": [500.0, 500.0, 500.0, 500.0],
            "meeting_date": ["2025-01-15", "2025-01-15", "2025-02-01", "2025-02-01"],
            "track_code": ["MX", "MX", "GP", "GP"],
            "speed_discard": [0, 1, 0, 0],
            "speed_rating": [10.0, 9.0, 11.0, 10.5],
            "speed_rank": [1, 2, 1, 1],
            "split": ["holdout_2025"] * 4,
        }
    )


def test_max_drawdown_and_monthly_equity(tmp_path):
    bets = select_frozen_bets(_synthetic_frame())
    assert len(bets) == 3  # model rank 1, speed ok, BSP band, volume

    # Two wins (+2.76 each net) then one loss: peak +2.76, trough 0, then +5.52
    assert max_drawdown(bets["pnl"]) == -1.0

    curve = equity_curve(bets)
    assert list(curve.columns) == ["date", "pnl", "equity"]
    assert len(curve) == 2
    jan = curve.loc[curve["date"] == "2025-01-15"].iloc[0]
    feb = curve.loc[curve["date"] == "2025-02-01"].iloc[0]
    assert jan["pnl"] == bets.loc[bets["meeting_date"].eq("2025-01-15"), "pnl"].sum()
    assert feb["equity"] == curve["pnl"].sum()

    book_path = tmp_path / "book.txt"
    equity_path = tmp_path / "equity.csv"
    write_frozen_book(_synthetic_frame(), book_path=book_path, equity_path=equity_path)
    text = book_path.read_text(encoding="utf-8")
    assert "2025-01" in text
    assert "2025-02" in text
    assert book_path.exists() and equity_path.exists()
