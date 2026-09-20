"""Command-line entrypoint: python -m brownlow <command>"""

import argparse

import config
from brownlow.merge import merge_afl_data
from brownlow.predict import run_predict
from brownlow.scrape import download_afl_player_data, download_and_parse_game_data


def scrape_games() -> None:
    config.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    download_and_parse_game_data(config.GAME_DATA_PATH)


def scrape_players(year: int | None = None) -> None:
    season = year if year is not None else config.SCRAPE_PLAYER_YEAR
    path = config.player_data_path(season)
    path.parent.mkdir(parents=True, exist_ok=True)
    download_afl_player_data(season, path)


def merge() -> None:
    merge_afl_data()


def predict(tune: bool = False) -> None:
    run_predict(tune=tune)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m brownlow",
        description="Brownlow Medal prediction pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scrape-games", help="Download and parse AFL game results")

    players_parser = subparsers.add_parser(
        "scrape-players", help="Download player stats for a season"
    )
    players_parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=f"Season to scrape (default: {config.SCRAPE_PLAYER_YEAR})",
    )

    subparsers.add_parser("merge", help="Merge player and game data")

    predict_parser = subparsers.add_parser(
        "predict", help="Train the model and export predictions"
    )
    predict_parser.add_argument(
        "--tune",
        action="store_true",
        help="Run GridSearchCV before the default training path",
    )

    all_parser = subparsers.add_parser("all", help="Run scrape, merge, and predict in order")
    all_parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=f"Season to scrape for player stats (default: {config.SCRAPE_PLAYER_YEAR})",
    )
    all_parser.add_argument(
        "--tune",
        action="store_true",
        help="Run GridSearchCV before the default training path",
    )

    args = parser.parse_args(argv)

    if args.command == "scrape-games":
        scrape_games()
    elif args.command == "scrape-players":
        scrape_players(args.year)
    elif args.command == "merge":
        merge()
    elif args.command == "predict":
        predict(tune=args.tune)
    elif args.command == "all":
        scrape_games()
        scrape_players(args.year)
        merge()
        predict(tune=args.tune)
