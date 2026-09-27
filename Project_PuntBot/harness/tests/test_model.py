"""Unit tests for walk-forward and calendar-year holdout training."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

import config
from puntbot.features import FEATURE_COLUMNS
from puntbot.model import holdout_year_predict, walk_forward_predict


def _synthetic_features() -> pd.DataFrame:
    """Tiny multi-year frame with dummy feature columns."""
    rows = []
    market_id = 1
    for year in (2023, 2024, 2025):
        months = (1, 2, 3, 4, 5) if year < 2025 else (6,)
        for month in months:
            for runner in range(4):
                row = {col: float(runner + 1) for col in FEATURE_COLUMNS}
                row.update(
                    {
                        "meeting_date": f"{year}-{month:02d}-15",
                        "win_market_id": market_id,
                        "win_bsp": 3.0 + runner * 0.5,
                        "won": int(runner == 0),
                        "field_size": 4,
                    }
                )
                rows.append(row)
                market_id += 1
    return pd.DataFrame(rows)


def test_walk_forward_predict_default_still_works():
    frame = _synthetic_features()
    result = walk_forward_predict(frame)

    assert not result.empty
    assert "model_p" in result.columns
    assert "raw_p" in result.columns
    assert result["split"].astype(str).str.startswith("202").all()
    assert pd.to_datetime(result["meeting_date"]).dt.year.max() <= 2025


def test_holdout_year_does_not_train_on_holdout_labels():
    frame = _synthetic_features()
    captured: dict[str, object] = {}

    def fake_fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        captured["train_years"] = sorted(pd.to_datetime(train["meeting_date"]).dt.year.unique())
        captured["test_years"] = sorted(pd.to_datetime(test["meeting_date"]).dt.year.unique())
        return np.full(len(test), 0.2)

    with patch("puntbot.model._fit_predict", side_effect=fake_fit_predict):
        result = holdout_year_predict(frame, 2025)

    assert captured["train_years"] == [2023, 2024]
    assert captured["test_years"] == [2025]
    assert not result.empty
    assert (result["split"] == "holdout_2025").all()
    assert pd.to_datetime(result["meeting_date"]).dt.year.eq(2025).all()


def test_holdout_year_empty_when_no_holdout_rows(capsys):
    frame = _synthetic_features()
    frame = frame[pd.to_datetime(frame["meeting_date"]).dt.year < 2025]

    result = holdout_year_predict(frame, 2025)

    assert result.empty
    out = capsys.readouterr().out
    assert "2025" in out
    assert "No joined rows" in out
