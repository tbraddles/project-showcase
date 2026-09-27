"""Why does the 2025 holdout start in August?"""

import sqlite3

import pandas as pd

import config


def month_counts(series: pd.Series, year: int) -> None:
    dates = pd.to_datetime(series)
    months = dates[dates.dt.year == year].dt.to_period("M").value_counts().sort_index()
    print(months.to_string() if not months.empty else "  (none)")


def main() -> None:
    con = sqlite3.connect(config.DB_PATH)
    races = pd.read_sql("select date, track from races", con)
    print("races 2025 by month")
    month_counts(races["date"], 2025)

    matches = pd.read_sql(
        "select meeting_date from runner_matches",
        con,
    )
    print("runner_matches 2025 by month")
    month_counts(matches["meeting_date"], 2025)
    con.close()

    features = pd.read_csv(config.FEATURES_PATH, usecols=["meeting_date"])
    print("features 2025 by month")
    month_counts(features["meeting_date"], 2025)

    preds = pd.read_csv(config.PREDICTIONS_PATH, usecols=["meeting_date", "split"])
    print("predictions split", preds["split"].value_counts().to_dict())
    print("predictions 2025 by month")
    month_counts(preds["meeting_date"], 2025)


if __name__ == "__main__":
    main()
