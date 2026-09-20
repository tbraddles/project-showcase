"""Train / evaluate the Brownlow vote classifier."""

import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix

import config


def prepare_model_data(
    df,
    feature_cols: list[str] | None = None,
    predict_year: int | None = None,
    val_year: int | None = None,
) -> tuple:
    """
    Split by season: train on earlier years, validate on val_year, predict predict_year.

    Returns:
        tuple: X_train, X_val, y_train, y_val, predict_df
    """
    feature_cols = feature_cols if feature_cols is not None else config.FEATURE_COLS
    predict_year = predict_year if predict_year is not None else config.PREDICT_YEAR
    val_year = val_year if val_year is not None else config.VAL_YEAR

    predict_df = df[df["year"] == predict_year].copy()
    val_df = df[df["year"] == val_year].copy()
    train_df = df[df["year"] < val_year].copy()

    print(f"Train years: {sorted(train_df['year'].unique().tolist())}")
    print(f"Validation year: {val_year} ({len(val_df)} rows)")
    print(f"Predict year: {predict_year} ({len(predict_df)} rows)")

    train_df["brownlow_binary"] = (train_df["brownlow"] > 0).astype(int)
    val_df["brownlow_binary"] = (val_df["brownlow"] > 0).astype(int)

    X_train = train_df[feature_cols]
    y_train = train_df["brownlow_binary"]
    X_val = val_df[feature_cols]
    y_val = val_df["brownlow_binary"]
    print("Train class distribution:\n", y_train.value_counts(normalize=True))
    if y_val.sum() == 0:
        print(
            f"Warning: {val_year} has no Brownlow labels. "
            "Threshold reports and ranking metrics will be meaningless."
        )

    return X_train, X_val, y_train, y_val, predict_df, val_df


def train_xgb_model(X_train, y_train, X_val, y_val) -> tuple:
    """
    Train XGBoost binary classifier with early stopping on the validation season.

    Returns:
        tuple: (trained booster, validation-set probabilities)
    """
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "scale_pos_weight": 10,
        "seed": 42,
        "eta": 0.03,
        "max_depth": 9,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 1,
    }

    evallist = [(dtrain, "train"), (dval, "eval")]
    bst = xgb.train(
        params,
        dtrain,
        100,
        evals=evallist,
        early_stopping_rounds=10,
        verbose_eval=10,
    )

    probs = bst.predict(dval)
    return bst, probs


def evaluate_thresholds(probs, y_true, threshold):
    """Print classification reports and confusion matrices for a threshold."""
    y_pred = (probs >= threshold).astype(int)
    print(f"\nClassification Report at threshold {threshold}:")
    print(classification_report(y_true, y_pred, zero_division=0))
    print(f"Confusion Matrix at threshold {threshold}:")
    print(confusion_matrix(y_true, y_pred))


def assign_321_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Award 3-2-1 votes to the top three predicted players in each game."""
    ranked = df.sort_values(["game_id", "vote_probability"], ascending=[True, False])
    ranked["votes"] = ranked.groupby("game_id").cumcount().map({0: 3, 1: 2, 2: 1}).fillna(0)
    return ranked


def evaluate_vote_ranking(val_df: pd.DataFrame, probs) -> dict:
    """
    Score the medal task: per-game 3-2-1 ranking and season-total correlation.

    Returns a metrics dict and prints a short report.
    """
    scored = val_df.copy()
    scored["vote_probability"] = probs
    scored = scored[scored["game_id"].notna()].copy()
    if scored.empty:
        print("\nVote ranking: skipped (no game_id on validation rows).")
        return {}
    scored = assign_321_votes(scored)

    n_games = scored["game_id"].nunique()
    actual_voters = scored[scored["brownlow"] > 0]
    if actual_voters.empty:
        print("\nVote ranking: skipped (no Brownlow labels in the validation year).")
        return {}

    top3_recall = float((actual_voters["votes"] > 0).mean())
    exact_on_voters = float((actual_voters["votes"] == actual_voters["brownlow"]).mean())
    bog_actual = scored[scored["brownlow"] == 3]
    bog_accuracy = float((bog_actual["votes"] == 3).mean()) if len(bog_actual) else 0.0

    season = scored.groupby(["player", "team"], as_index=False).agg(
        actual=("brownlow", "sum"),
        predicted=("votes", "sum"),
    )
    spearman = float(season["actual"].corr(season["predicted"], method="spearman"))
    actual_winner = season.sort_values("actual", ascending=False).iloc[0]
    predicted_winner = season.sort_values("predicted", ascending=False).iloc[0]

    print("\nBrownlow ranking metrics (validation season):")
    print(f"  Games: {n_games}")
    print(f"  Top-3 recall (actual vote-getters in predicted top 3): {top3_recall:.3f}")
    print(f"  Exact 3-2-1 match on actual vote-getters: {exact_on_voters:.3f}")
    print(f"  Best-on-ground accuracy (predicted 3 == actual 3): {bog_accuracy:.3f}")
    print(f"  Season-total Spearman correlation: {spearman:.3f}")
    print(
        f"  Actual leader: {actual_winner['player']} ({int(actual_winner['actual'])} votes) · "
        f"Predicted leader: {predicted_winner['player']} ({int(predicted_winner['predicted'])} votes)"
    )

    return {
        "games": n_games,
        "top3_recall": top3_recall,
        "exact_on_voters": exact_on_voters,
        "bog_accuracy": bog_accuracy,
        "season_spearman": spearman,
        "actual_leader": actual_winner["player"],
        "actual_leader_votes": int(actual_winner["actual"]),
        "predicted_leader": predicted_winner["player"],
        "predicted_leader_votes": int(predicted_winner["predicted"]),
        "season": season,
    }
