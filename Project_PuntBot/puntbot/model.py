"""Walk-forward form-only win probability model."""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

import config
from puntbot.features import FEATURE_COLUMNS, write_features


def month_key(dates: pd.Series) -> pd.Series:
    return pd.to_datetime(dates).dt.to_period("M").astype(str)


def normalize_race_probs(frame: pd.DataFrame, prob_col: str = "raw_p") -> pd.Series:
    totals = frame.groupby("win_market_id")[prob_col].transform("sum")
    return np.where(totals > 0, frame[prob_col] / totals, np.nan)


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    model = HistGradientBoostingClassifier(
        max_depth=3,
        learning_rate=0.08,
        max_iter=150,
        min_samples_leaf=20,
        random_state=config.RANDOM_SEED,
    )
    x_train = train[FEATURE_COLUMNS]
    y_train = train["won"].astype(int)
    if y_train.nunique() < 2 or len(train) < 50:
        field = test["field_size"].replace(0, np.nan)
        return (1.0 / field).to_numpy()
    model.fit(x_train, y_train)
    return model.predict_proba(test[FEATURE_COLUMNS])[:, 1]


def walk_forward_predict(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    frame = frame.dropna(subset=["win_market_id", "win_bsp"])
    frame["month"] = month_key(frame["meeting_date"])
    months = sorted(frame["month"].unique())
    predictions = []

    if len(months) < config.WALK_FORWARD_MIN_TRAIN_MONTHS + 1:
        parsed = pd.to_datetime(frame["meeting_date"])
        cutoff = parsed.quantile(0.70)
        train = frame[parsed <= cutoff]
        test = frame[parsed > cutoff]
        if test.empty or train.empty:
            raise SystemExit(
                "Not enough joined form+Betfair rows to train a model. "
                "Scrape a longer date range, then re-run join / features / train."
            )
        test = test.copy()
        test["raw_p"] = _fit_predict(train, test)
        test["model_p"] = normalize_race_probs(test)
        test["split"] = "holdout"
        return test

    history = []
    for i, month in enumerate(months):
        history.append(month)
        if i < config.WALK_FORWARD_MIN_TRAIN_MONTHS:
            continue
        train = frame[frame["month"].isin(history[:-1])]
        test = frame[frame["month"] == month].copy()
        if test.empty or train.empty:
            continue
        test["raw_p"] = _fit_predict(train, test)
        test["model_p"] = normalize_race_probs(test)
        test["split"] = month
        predictions.append(test)

    if not predictions:
        raise SystemExit("Walk-forward produced no test months.")
    return pd.concat(predictions, ignore_index=True)


def run_train(rebuild_features: bool = True) -> pd.DataFrame:
    features = write_features() if rebuild_features else pd.read_csv(config.FEATURES_PATH)
    if features.empty:
        raise SystemExit("No feature rows. Run the form scrape and join first.")
    predicted = walk_forward_predict(features)
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    predicted.to_csv(config.PREDICTIONS_PATH, index=False)
    print(
        f"Wrote {len(predicted):,} out-of-sample predictions "
        f"({predicted['win_market_id'].nunique():,} markets) to {config.PREDICTIONS_PATH}"
    )
    return predicted


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train the form-only win model")
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Reuse data/processed/features.csv instead of rebuilding",
    )
    args = parser.parse_args(argv)
    run_train(rebuild_features=not args.no_rebuild)
