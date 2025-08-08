"""
xgb_tuning_utils.py

This module provides a utility function for hyperparameter tuning of an XGBoost classifier
using GridSearchCV. The function performs model fitting, prints evaluation metrics, and
returns the best model found.

Can be imported and used within a larger project or run independently for testing.
"""
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix

def tune_xgb_classifier(X_train, y_train, X_test, y_test) -> XGBClassifier:
    """
    Performs hyperparameter tuning for an XGBoost classifier using GridSearchCV.

    Args:
        X_train (pd.DataFrame): Training features.
        y_train (pd.Series): Training labels.
        X_test (pd.DataFrame): Testing features.
        y_test (pd.Series): Testing labels.

    Returns:
        XGBClassifier: The best estimator found by GridSearchCV.
    """
    xgb_clf = XGBClassifier(
        objective='binary:logistic',
        use_label_encoder=False,
        eval_metric='logloss',
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        random_state=42
    )

    param_grid = {
        'max_depth': [7, 9],
        'learning_rate': [0.02, 0.03],
        'n_estimators': [300, 400],
        'subsample': [0.7, 0.8],
        'colsample_bytree': [0.7, 0.8],
        'scale_pos_weight': [10, 12],
        'gamma': [1, 5],
    }

    grid_search = GridSearchCV(
        estimator=xgb_clf,
        param_grid=param_grid,
        scoring='f1',
        cv=3,
        verbose=2,
        n_jobs=-1
    )

    grid_search.fit(X_train, y_train)

    print("Best parameters found: ", grid_search.best_params_)

    # Use best estimator for prediction
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test) # Predict and evaluate on test set

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    return best_model

def main():
    """
    Placeholder main function for local testing.
    Replace with real data to test the tuner independently.
    """
    print("This module is intended to be imported and used in a pipeline.")
    print("To test standalone, load your train/test sets and call `tune_xgb_classifier`.")

if __name__ == "__main__":
    main()