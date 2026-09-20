"""Merge yearly player stats with game scores into a master dataset."""

from pathlib import Path

import pandas as pd

import config
from brownlow.columns import standardize_columns


def normalize_players(data_players: pd.DataFrame) -> pd.DataFrame:
    """Keep home-and-away rounds only, coerce types, and standardize text."""
    players = standardize_columns(data_players.copy())
    # Finals use letter codes (QF, EF, SF, PF, GF, WF, ...). Keep numbered rounds.
    home_and_away = players["round"].astype(str).str.fullmatch(r"\d+")
    players = players[home_and_away].copy()
    players["round"] = players["round"].astype(int)

    for col in ["team", "opponent", "player"]:
        if col in players.columns:
            players[col] = players[col].astype(str).str.strip().str.upper()

    for col in ["year", "round"]:
        if col in players.columns:
            players[col] = players[col].astype(int)

    return players


def normalize_games(data_scores: pd.DataFrame) -> pd.DataFrame:
    """Keep home-and-away games after 2009 and attach team codes."""
    games = standardize_columns(data_scores.copy())
    games = games[(games["year"] > 2009) & (games["game_type"] == "HA")].copy()

    games["home_team_code"] = games["home_team"].map(config.TEAM_CODE_MAP).str.upper()
    games["away_team_code"] = games["away_team"].map(config.TEAM_CODE_MAP).str.upper()

    for col in ["home_team_code", "away_team_code", "home_team", "away_team"]:
        if col in games.columns:
            games[col] = games[col].astype(str).str.strip().str.upper()

    for col in ["year", "round"]:
        if col in games.columns:
            games[col] = games[col].astype(int)

    return games


def join_players_to_games(players: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """
    Join each player-game row to its match by stacking games once per team.

    A home view and an away view of each match are concatenated, then joined
    on year, round, team, and opponent. This replaces the old double-merge
    plus row-wise _x/_y coalesce.
    """
    home = games.assign(team=games["home_team_code"], opponent=games["away_team_code"])
    away = games.assign(team=games["away_team_code"], opponent=games["home_team_code"])
    games_long = pd.concat([home, away], ignore_index=True)

    return players.merge(games_long, on=["year", "round", "team", "opponent"], how="left")


def merge_afl_data(
    raw_dir: str | Path | None = None,
    player_years: list[int] | None = None,
    output_file: str | Path | None = None,
) -> pd.DataFrame:
    """
    Load yearly player and game CSVs, clean them, join into one table, and save.

    Returns the merged DataFrame.
    """
    tables_dir = Path(raw_dir) if raw_dir is not None else config.DATA_RAW_DIR
    years = player_years if player_years is not None else config.PLAYER_YEARS
    output_path = Path(output_file) if output_file is not None else config.PROCESSED_DATA_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    player_dfs = []
    for year in years:
        df = pd.read_csv(tables_dir / f"{year}_AFL_Player_Data.csv")
        df["Year"] = year
        player_dfs.append(df)
    players = normalize_players(pd.concat(player_dfs, ignore_index=True))
    games = normalize_games(pd.read_csv(tables_dir / "AFL_Game_Data.csv"))
    player_games = join_players_to_games(players, games)

    player_games.to_csv(output_path, index=False)
    print(f"Merge complete and saved to {output_path}")
    return player_games
