"""Train / evaluate a per-game Brownlow ranker."""

import pandas as pd
import xgboost as xgb

import config

RANK_PARAMS = {
    "objective": "rank:ndcg",
    "eval_metric": "ndcg@3",
    "seed": 42,
    "eta": 0.03,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma": 1,
}


def labeled_years(df: pd.DataFrame, before_year: int | None = None) -> list[int]:
    """Seasons that have at least one official Brownlow vote."""
    years = []
    for year, group in df.groupby("year"):
        year = int(year)
        if before_year is not None and year >= before_year:
            continue
        if (group["brownlow"] > 0).any():
            years.append(year)
    return sorted(years)


def prepare_model_data(
    df,
    feature_cols: list[str] | None = None,
    predict_year: int | None = None,
    val_year: int | None = None,
) -> tuple:
    """
    Split by season: train on earlier years, validate on val_year, predict predict_year.

    Drops rows with no game_id so the ranker can group by match.
    """
    feature_cols = feature_cols if feature_cols is not None else config.FEATURE_COLS
    predict_year = predict_year if predict_year is not None else config.PREDICT_YEAR
    val_year = val_year if val_year is not None else config.VAL_YEAR

    usable = df[df["game_id"].notna()].copy()
    predict_df = usable[usable["year"] == predict_year].copy()
    val_df = usable[usable["year"] == val_year].copy()
    train_df = usable[usable["year"] < val_year].copy()

    print(f"Train years: {sorted(train_df['year'].unique().tolist())}")
    print(f"Validation year: {val_year} ({len(val_df)} rows)")
    print(f"Predict year: {predict_year} ({len(predict_df)} rows)")
    print("Train Brownlow vote counts:\n", train_df["brownlow"].value_counts().sort_index())
    if (val_df["brownlow"] > 0).sum() == 0:
        print(
            f"Warning: {val_year} has no Brownlow labels. "
            "Ranking metrics will be meaningless."
        )

    missing = [col for col in feature_cols if col not in usable.columns]
    if missing:
        raise KeyError(f"Missing feature columns: {missing}")

    return train_df, val_df, predict_df


def _sort_for_ranking(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["game_id", "player_id"], kind="mergesort").reset_index(drop=True)


def to_rank_dmatrix(df: pd.DataFrame, feature_cols: list[str]) -> tuple[xgb.DMatrix, pd.DataFrame]:
    """Build a DMatrix grouped by game. Rows are sorted by game_id."""
    frame = _sort_for_ranking(df)
    dmat = xgb.DMatrix(frame[feature_cols], label=frame["brownlow"].astype(float))
    group_sizes = frame.groupby("game_id", sort=False).size().to_list()
    dmat.set_group(group_sizes)
    return dmat, frame


def train_ranker(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    params: dict | None = None,
    num_boost_round: int = 100,
    verbose: bool = True,
) -> tuple:
    """
    Train XGBoost rank:ndcg with Brownlow 0/1/2/3 as relevance grades.

    Returns (booster, validation frame in rank order, validation scores).
    """
    feature_cols = feature_cols if feature_cols is not None else config.FEATURE_COLS
    fit_params = {**RANK_PARAMS, **(params or {})}

    dtrain, _ = to_rank_dmatrix(train_df, feature_cols)
    dval, val_sorted = to_rank_dmatrix(val_df, feature_cols)

    evallist = [(dtrain, "train"), (dval, "eval")]
    bst = xgb.train(
        fit_params,
        dtrain,
        num_boost_round,
        evals=evallist,
        early_stopping_rounds=10,
        verbose_eval=10 if verbose else False,
    )
    scores = bst.predict(dval)
    return bst, val_sorted, scores


def assign_321_votes(df: pd.DataFrame, score_col: str = "vote_probability") -> pd.DataFrame:
    """Award 3-2-1 votes to the top three predicted players in each game."""
    ranked = df.sort_values(["game_id", score_col], ascending=[True, False])
    ranked["votes"] = ranked.groupby("game_id").cumcount().map({0: 3, 1: 2, 2: 1}).fillna(0)
    return ranked


def evaluate_vote_ranking(val_df: pd.DataFrame, scores, label: str | None = None) -> dict:
    """
    Score the medal task: per-game 3-2-1 ranking and season-total correlation.
    """
    scored = val_df.copy()
    scored["vote_probability"] = scores
    scored = scored[scored["game_id"].notna()].copy()
    if scored.empty:
        print("\nVote ranking: skipped (no game_id on validation rows).")
        return {}
    scored = assign_321_votes(scored)

    n_games = scored["game_id"].nunique()
    actual_voters = scored[scored["brownlow"] > 0]
    title = f" ({label})" if label else ""
    if actual_voters.empty:
        print(f"\nVote ranking{title}: skipped (no Brownlow labels).")
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

    print(f"\nBrownlow ranking metrics{title}:")
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
        "label": label,
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


def walk_forward_evaluate(df: pd.DataFrame, feature_cols: list[str] | None = None) -> list[dict]:
    """Train on earlier seasons and score each labeled holdout year."""
    feature_cols = feature_cols if feature_cols is not None else config.FEATURE_COLS
    holdouts = labeled_years(df, before_year=config.PREDICT_YEAR)[-3:]
    results = []
    print("\n=== Walk-forward ranking ===")
    for val_year in holdouts:
        train_df = df[(df["year"] < val_year) & df["game_id"].notna()].copy()
        val_df = df[(df["year"] == val_year) & df["game_id"].notna()].copy()
        if train_df.empty or val_df.empty or (val_df["brownlow"] > 0).sum() == 0:
            continue
        if train_df["year"].nunique() < 1:
            continue
        _, val_sorted, scores = train_ranker(
            train_df, val_df, feature_cols, verbose=False
        )
        metrics = evaluate_vote_ranking(val_sorted, scores, label=str(val_year))
        if metrics:
            results.append(metrics)

    if results:
        print("\nWalk-forward summary:")
        print(f"{'Year':<8}{'Top-3':>8}{'Exact':>8}{'BOG':>8}{'Spearman':>10}")
        for row in results:
            print(
                f"{row['label']:<8}{row['top3_recall']:>8.3f}"
                f"{row['exact_on_voters']:>8.3f}{row['bog_accuracy']:>8.3f}"
                f"{row['season_spearman']:>10.3f}"
            )
        print(
            f"{'mean':<8}"
            f"{sum(r['top3_recall'] for r in results) / len(results):>8.3f}"
            f"{sum(r['exact_on_voters'] for r in results) / len(results):>8.3f}"
            f"{sum(r['bog_accuracy'] for r in results) / len(results):>8.3f}"
            f"{sum(r['season_spearman'] for r in results) / len(results):>10.3f}"
        )
    return results
