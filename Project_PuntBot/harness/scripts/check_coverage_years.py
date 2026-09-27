"""Form vs Betfair monthly coverage for core years."""

import sqlite3

import pandas as pd

import config


def by_month(con, sql: str, year: int) -> pd.Series:
    frame = pd.read_sql(sql, con)
    dates = pd.to_datetime(frame.iloc[:, 0])
    return dates[dates.dt.year == year].dt.to_period("M").value_counts().sort_index()


def main() -> None:
    con = sqlite3.connect(config.DB_PATH)
    for year in (2023, 2024, 2025, 2026):
        print(f"\n=== {year} form races ===")
        print(by_month(con, "select date from races", year).to_string() or "(none)")
        print(f"=== {year} betfair distinct meetings (AU) ===")
        print(
            by_month(
                con,
                "select meeting_date from betfair_runners where upper(coalesce(state_code,'')) in ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')",
                year,
            ).to_string()
            or "(none)"
        )
    con.close()


if __name__ == "__main__":
    main()
