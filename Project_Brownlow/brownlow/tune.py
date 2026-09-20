"""Optional GridSearchCV tuner for the XGBoost classifier."""

from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV
from xgboost import XGBClassifier


def tune_xgb_classifier(X_train, y_train, X_val, y_val) -> XGBClassifier:
    """
    Hyperparameter-tune an XGBoost classifier with GridSearchCV.

    Evaluates the best estimator on the held-out validation season.
    """
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    xgb_clf = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=pos_weight,
        random_state=42,
    )

    param_grid = {
        "max_depth": [7, 9],
        "learning_rate": [0.02, 0.03],
        "n_estimators": [300, 400],
        "subsample": [0.7, 0.8],
        "colsample_bytree": [0.7, 0.8],
        "scale_pos_weight": [10, 12],
        "gamma": [1, 5],
    }

    grid_search = GridSearchCV(
        estimator=xgb_clf,
        param_grid=param_grid,
        scoring="f1",
        cv=3,
        verbose=2,
        n_jobs=-1,
    )
    grid_search.fit(X_train, y_train)

    print("Best parameters found: ", grid_search.best_params_)

    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_val)

    print("\nClassification Report:")
    print(classification_report(y_val, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_val, y_pred))

    return best_model
