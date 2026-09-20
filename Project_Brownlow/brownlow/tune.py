"""Small grid search for the per-game XGBoost ranker."""

from itertools import product

from brownlow.model import evaluate_vote_ranking, train_ranker


def tune_xgb_ranker(train_df, val_df, feature_cols):
    """
    Try a small ranker grid and keep the booster with the best top-3 recall.

    Returns (booster, validation frame, scores) like train_ranker.
    """
    grid = {
        "max_depth": [4, 6],
        "eta": [0.03, 0.05],
        "min_child_weight": [1, 5],
    }

    best = None
    best_pack = None
    print("\nTuning ranker on validation top-3 recall...")
    for max_depth, eta, min_child_weight in product(
        grid["max_depth"], grid["eta"], grid["min_child_weight"]
    ):
        params = {
            "max_depth": max_depth,
            "eta": eta,
            "min_child_weight": min_child_weight,
        }
        bst, val_sorted, scores = train_ranker(
            train_df, val_df, feature_cols, params=params, verbose=False
        )
        metrics = evaluate_vote_ranking(
            val_sorted,
            scores,
            label=f"tune depth={max_depth} eta={eta} mcw={min_child_weight}",
        )
        score = metrics.get("top3_recall", 0.0)
        if best is None or score > best:
            best = score
            best_pack = (bst, val_sorted, scores, params)

    bst, val_sorted, scores, params = best_pack
    print(f"Best tune params: {params} (top-3 recall {best:.3f})")
    return bst, val_sorted, scores
