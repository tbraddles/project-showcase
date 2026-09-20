"""Load processed data, run the model, and export vote predictions."""

from pathlib import Path

import pandas as pd
import xgboost as xgb

import config
from brownlow.columns import standardize_columns
from brownlow.features import engineer_features, load_vote_backfills
from brownlow.model import (
    assign_321_votes,
    evaluate_thresholds,
    evaluate_vote_ranking,
    prepare_model_data,
    train_xgb_model,
)


def load_data(file_path: str | Path) -> pd.DataFrame:
    """Load AFL player-game data and normalize any legacy column names."""
    return standardize_columns(pd.read_csv(file_path))


def predict_and_export(bst, predict_df, feature_cols, output_dir=None, predict_year: int | None = None):
    """Predict vote probabilities, assign 3-2-1 votes, and write year-scoped heatmaps."""
    predict_year = predict_year if predict_year is not None else config.PREDICT_YEAR
    output_dir = Path(output_dir) if output_dir is not None else config.year_output_dir(predict_year)
    output_dir.mkdir(parents=True, exist_ok=True)

    dpredict = xgb.DMatrix(predict_df[feature_cols])
    predict_df = predict_df.copy()
    predict_df["vote_probability"] = bst.predict(dpredict)

    predict_df["adjusted_round"] = predict_df["round"] - 1  # opening round is 0
    predict_df.to_csv(
        config.prediction_csv_path("player_game_probabilities", predict_year),
        index=False,
    )

    pivot_df = predict_df.pivot_table(
        index=["player", "team"], columns="adjusted_round", values="vote_probability", fill_value=0
    )
    pivot_df.columns = [f"round_{int(col)}" for col in pivot_df.columns]
    pivot_df["total_predicted_votes"] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values(by="total_predicted_votes", ascending=False)
    pivot_df = pivot_df.drop(columns=["total_predicted_votes"])
    pivot_df.to_csv(config.prediction_csv_path("heatmap_probability", predict_year))

    predict_df = assign_321_votes(predict_df)

    pivot_votes = predict_df.pivot_table(
        index=["player", "team"],
        columns="adjusted_round",
        values="votes",
        aggfunc="sum",
        fill_value=0,
    )
    pivot_votes.columns = [f"round_{int(col)}" for col in pivot_votes.columns]
    pivot_votes["total_votes"] = pivot_votes.sum(axis=1)
    pivot_votes = pivot_votes.sort_values("total_votes", ascending=False)
    pivot_votes.to_csv(config.prediction_csv_path("heatmap_votes", predict_year))

    print(f"Wrote {predict_year} predictions to {output_dir}")


def run_predict(tune: bool = False) -> None:
    """End-to-end train and export using config defaults."""
    season_dir = config.year_output_dir(config.PREDICT_YEAR)
    season_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(config.PROCESSED_DATA_PATH)
    vote_backfills = load_vote_backfills()
    df = engineer_features(df, vote_backfills, output_path=config.FEATURE_ENGINEERING_PATH)

    X_train, X_val, y_train, y_val, predict_df, val_df = prepare_model_data(
        df, config.FEATURE_COLS, config.PREDICT_YEAR, config.VAL_YEAR
    )

    if tune:
        from brownlow.tune import tune_xgb_classifier

        model = tune_xgb_classifier(X_train, y_train, X_val, y_val)
        bst = model.get_booster()
        probs = model.predict_proba(X_val)[:, 1]
    else:
        bst, probs = train_xgb_model(X_train, y_train, X_val, y_val)

    for threshold in config.EVAL_THRESHOLDS:
        evaluate_thresholds(probs, y_val, threshold)
    evaluate_vote_ranking(val_df, probs)

    predict_and_export(bst, predict_df, config.FEATURE_COLS, season_dir, config.PREDICT_YEAR)
