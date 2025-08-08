"""
player_data_scraper.py

Downloads AFL player stats for a specified year from AFL Tables and saves them to a local CSV file.
"""

import pandas as pd
import requests
import io

def download_afl_player_data(year: int, save_path: str) -> None:
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
        data['Year'] = year
        data.to_csv(save_path, index=False)
        print(f"Downloaded and saved data for {year}.")
    except Exception as e:
        print(f"Failed to download data for {year}: {e}")

if __name__ == "__main__":
    year = 2025
    output_path = fr"C:\Users\tyler\Documents\CodingProjects\Brownlow\afl_tables\{year}_AFL_Player_Data.csv"
    download_afl_player_data(year, output_path)