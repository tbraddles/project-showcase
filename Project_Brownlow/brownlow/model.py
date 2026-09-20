"""Train / evaluate the Brownlow vote classifier."""

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

    return X_train, X_val, y_train, y_val, predict_df


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
    print(classification_report(y_true, y_pred))
    print(f"Confusion Matrix at threshold {threshold}:")
    print(confusion_matrix(y_true, y_pred))
