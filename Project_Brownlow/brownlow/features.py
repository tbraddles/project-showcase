"""Domain feature engineering and Brownlow vote backfill loading."""

from pathlib import Path

import numpy as np
import pandas as pd

import config
from brownlow.columns import standardize_columns


def load_vote_backfills(path: str | Path | None = None) -> dict[int, dict[str, int]]:
    """Load official season tallies used when past_votes cannot be shifted."""
    vote_path = Path(path) if path is not None else config.VOTE_BACKFILL_PATH
    votes_df = pd.read_csv(vote_path)
    backfills: dict[int, dict[str, int]] = {}
    for year, group in votes_df.groupby("year"):
        backfills[int(year)] = dict(zip(group["player"], group["votes"].astype(int)))
    return backfills


def engineer_features(
    df: pd.DataFrame,
    vote_backfills: dict[int, dict[str, int]] | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Apply domain-specific feature engineering to the AFL player data.

    Adds:
        - Margin calculation
        - Past Brownlow votes
        - Disposals per time
        - Interaction and ratio features
    """
    df = standardize_columns(df.copy())
    if vote_backfills is None:
        vote_backfills = load_vote_backfills()

    max_score = df[["home_total", "away_total"]].max(axis=1).replace(0, 1)
    margin_pts = np.select(
        [
            df["team"] == df["home_team_code"],
            df["team"] == df["away_team_code"],
        ],
        [
            df["home_total"] - df["away_total"],
            df["away_total"] - df["home_total"],
        ],
        default=0,
    )
    df["margin"] = margin_pts / max_score

    season_votes = df.groupby(["player_id", "year"])["brownlow"].sum().reset_index()
    season_votes.rename(columns={"brownlow": "season_votes"}, inplace=True)
    season_votes["past_votes"] = season_votes.groupby("player_id")["season_votes"].shift(1)
    df = df.merge(season_votes[["player_id", "year", "past_votes"]], on=["player_id", "year"], how="left")

    player_title = df["player"].str.title()
    for season_year, vote_year in config.VOTE_BACKFILL_YEARS.items():
        votes = vote_backfills[vote_year]
        mask = df["year"] == season_year
        df.loc[mask, "past_votes"] = player_title.loc[mask].map(votes)

    df["past_votes"] = df["past_votes"].fillna(0).astype(int)

    df["disposals"] = df["kicks"] + df["handballs"]
    df["disposals_per_time"] = df["disposals"] / df["pct_time_played"].replace(0, 1)
    df["goals_x_clearances"] = df["goals"] * df["clearances"]
    df["contested_possessions_x_tackles"] = df["contested_possessions"] * df["tackles"]
    df["clangers_x_frees_against"] = df["clangers"] * df["frees_against"]
    df["marks_inside_50_x_contested_marks"] = df["marks_inside_50"] * df["contested_marks"]
    df["goal_assists_x_inside_50"] = df["goal_assists"] * df["inside_50"]
    df["clearance_efficiency"] = df["clearances"] / df["contested_possessions"].replace(0, 1)
    df["tackles_clangers_ratio"] = df["tackles"] / df["clangers"].replace(0, 1)
    df["score_involvement"] = df["goals"] + df["goal_assists"]
    df["margin_x_past_votes"] = df["margin"] * df["past_votes"]
    df["rebounds_x_one_percenters"] = df["rebounds"] * df["one_percenters"]

    if output_path is not None:
        featured_path = Path(output_path)
        featured_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(featured_path, index=False)

    return df
