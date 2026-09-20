"""Download AFL player stats and game results from AFL Tables."""

import io
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


def download_afl_player_data(year: int, save_path: str | Path) -> None:
    """
    Downloads AFL player data for a given year and saves it to a CSV file.

    Args:
        year (int): The season year to download.
        save_path (str): The path where the CSV will be saved.
    """
    url = f"https://afltables.com/afl/stats/{year}_stats.txt"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = pd.read_csv(io.StringIO(response.text))
        data["Year"] = year
        data.to_csv(save_path, index=False)
        print(f"Downloaded and saved data for {year}.")
    except Exception as e:
        print(f"Failed to download data for {year}: {e}")


def download_and_parse_game_data(save_path: str | Path) -> None:
    """
    Downloads AFL game data from AFL Tables, parses it into a structured format,
    and saves it as a CSV file.

    Args:
        save_path (str): Path to save the output CSV file.
    """
    url = "https://afltables.com/afl/stats/biglists/bg3.txt"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to download game data: {e}")
        return

    lines = response.text.splitlines()

    pattern = (
        r"^(\d+)\.\s+(\d{1,2}-[A-Za-z]+-\d{4})\s+(\S+)\s+([A-Za-z\s]+?)\s+"
        r"(\d+)\.(\d+)\.(\d+)\s+([A-Za-z\s]+?)\s+(\d+)\.(\d+)\.(\d+)\s+(.+)$"
    )

    games = []
    for line in lines:
        match = re.match(pattern, line)
        if match:
            game_id = int(match.group(1))
            date_str = match.group(2)
            date_obj = datetime.strptime(date_str, "%d-%b-%Y")
            day_of_week = date_obj.strftime("%A")
            year = date_obj.year
            round_raw = match.group(3)
            if round_raw.startswith("R"):
                round_num = round_raw[1:]  # remove the 'R'
            else:
                round_num = round_raw
            game_type = "HA" if round_raw.startswith("R") else "F"

            games.append(
                {
                    "Game ID": game_id,
                    "Year": year,
                    "Game_Type": game_type,
                    "Round": round_num,
                    "Day": day_of_week,
                    "Home_Team": match.group(4).strip(),
                    "Away_Team": match.group(8).strip(),
                    "Venue": match.group(12).strip(),
                    "Home_Goals": int(match.group(5)),
                    "Home_Behinds": int(match.group(6)),
                    "Home_Total": int(match.group(7)),
                    "Away_Goals": int(match.group(9)),
                    "Away_Behinds": int(match.group(10)),
                    "Away_Total": int(match.group(11)),
                    "Date": date_obj.strftime("%Y-%m-%d"),
                }
            )

    df = pd.DataFrame(games)

    try:
        df.to_csv(save_path, index=False)
        print(f"Saved AFL game data to {save_path}")
    except Exception as e:
        print(f"Failed to save CSV file: {e}")
