"""
Shared pipeline settings.

Edit PREDICT_YEAR here when rolling the project forward. Paths, feature
columns, team codes, and evaluation thresholds all live in this module so
scrape / merge / train stay in sync.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"

PREDICT_YEAR = 2026

# 2023 player stats are incomplete, so that season is excluded from the merge.
PLAYER_YEARS = [2018, 2019, 2020, 2021, 2022, 2024, 2025, 2026]

# Last labeled season held out for early stopping and evaluation.
_PRIOR_YEARS = [year for year in PLAYER_YEARS if year < PREDICT_YEAR]
VAL_YEAR = max(_PRIOR_YEARS) if _PRIOR_YEARS else PREDICT_YEAR - 1

# Default player scrape matches the current prediction season.
SCRAPE_PLAYER_YEAR = PREDICT_YEAR

GAME_DATA_PATH = DATA_RAW_DIR / "AFL_Game_Data.csv"
PROCESSED_DATA_PATH = DATA_PROCESSED_DIR / "player_games.csv"
VOTE_BACKFILL_PATH = DATA_REFERENCE_DIR / "brownlow_votes.csv"
FEATURE_ENGINEERING_PATH = DATA_PROCESSED_DIR / "player_games_features.csv"

# Season year -> official Brownlow tally year used when past_votes is missing.
VOTE_BACKFILL_YEARS = {
    2024: 2023,
    2018: 2017,
}

TEAM_CODE_MAP = {
    "Adelaide": "AD",
    "Brisbane Lions": "BL",
    "Carlton": "CA",
    "Collingwood": "CW",
    "Essendon": "ES",
    "Fremantle": "FR",
    "Geelong": "GE",
    "Gold Coast": "GC",
    "GW Sydney": "GW",
    "Hawthorn": "HW",
    "Melbourne": "ME",
    "North Melbourne": "NM",
    "Port Adelaide": "PA",
    "Richmond": "RI",
    "St Kilda": "SK",
    "Sydney": "SY",
    "West Coast": "WC",
    "Western Bulldogs": "WB",
}

# AFL Tables / legacy headers -> snake_case names used after merge.
COLUMN_RENAME = {
    "Player": "player",
    "ID": "player_id",
    "Team": "team",
    "Opponent": "opponent",
    "Round": "round",
    "Kicks": "kicks",
    "Marks": "marks",
    "Hand Balls": "handballs",
    "Disp": "disp",
    "Goals": "goals",
    "Behinds": "behinds",
    "Hit Outs": "hit_outs",
    "Tackles": "tackles",
    "Rebounds": "rebounds",
    "Inside 50": "inside_50",
    "Clearances": "clearances",
    "Clangers": "clangers",
    "Frees For": "frees_for",
    "Frees Against": "frees_against",
    "Brownlow": "brownlow",
    "Contested Possessions": "contested_possessions",
    "Uncontested Possessions": "uncontested_possessions",
    "Contested Marks": "contested_marks",
    "Marks Inside 50": "marks_inside_50",
    "One Percenters": "one_percenters",
    "Bounces": "bounces",
    "Goal Assists": "goal_assists",
    "% Time Played": "pct_time_played",
    "Year": "year",
    "Game ID": "game_id",
    "Game_Type": "game_type",
    "Day": "day",
    "Home_Team": "home_team",
    "Away_Team": "away_team",
    "Venue": "venue",
    "Home_Goals": "home_goals",
    "Home_Behinds": "home_behinds",
    "Home_Total": "home_total",
    "Away_Goals": "away_goals",
    "Away_Behinds": "away_behinds",
    "Away_Total": "away_total",
    "Date": "date",
    "HT_Code": "home_team_code",
    "AT_Code": "away_team_code",
    "Time_Category": "time_category",
    "After_Game": "after_game",
    "Time": "time",
}

FEATURE_COLS = [
    "kicks",
    "handballs",
    "marks",
    "goals",
    "behinds",
    "hit_outs",
    "tackles",
    "rebounds",
    "inside_50",
    "clearances",
    "clangers",
    "frees_for",
    "frees_against",
    "contested_possessions",
    "uncontested_possessions",
    "contested_marks",
    "marks_inside_50",
    "one_percenters",
    "bounces",
    "goal_assists",
    "pct_time_played",
    "margin",
    "past_votes",
    "disposals_per_time",
    "goals_x_clearances",
    "contested_possessions_x_tackles",
    "clangers_x_frees_against",
    "marks_inside_50_x_contested_marks",
    "goal_assists_x_inside_50",
    "clearance_efficiency",
    "tackles_clangers_ratio",
    "score_involvement",
    "margin_x_past_votes",
    "rebounds_x_one_percenters",
]

EVAL_THRESHOLDS = [0.7, 0.5, 0.3]


def player_data_path(year: int) -> Path:
    return DATA_RAW_DIR / f"{year}_AFL_Player_Data.csv"


def year_output_dir(year: int | None = None) -> Path:
    """Prediction exports for one season, e.g. output/2025/."""
    season = year if year is not None else PREDICT_YEAR
    return OUTPUT_DIR / str(season)


def prediction_csv_path(name: str, year: int | None = None) -> Path:
    """Year-scoped output file, e.g. output/2025/brownlow_2025_heatmap_votes.csv."""
    season = year if year is not None else PREDICT_YEAR
    return year_output_dir(season) / f"brownlow_{season}_{name}.csv"
