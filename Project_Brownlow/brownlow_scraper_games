"""
Scrapes AFL match data from AFL Tables.
"""
import pandas as pd
import requests
import re
from datetime import datetime

# Load raw data from AFL Tables
url = "https://afltables.com/afl/stats/biglists/bg3.txt"
response = requests.get(url)
lines = response.text.splitlines()

# Parse each line into structured data
games = []
pattern = r'^(\d+)\.\s+(\d{1,2}-[A-Za-z]+-\d{4})\s+(\S+)\s+([A-Za-z\s]+?)\s+(\d+)\.(\d+)\.(\d+)\s+([A-Za-z\s]+?)\s+(\d+)\.(\d+)\.(\d+)\s+(.+)$'

for line in lines:
    match = re.match(pattern, line)
    if match:
        game_id = int(match.group(1))
        date_str = match.group(2)
        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
        day_of_week = date_obj.strftime('%A')
        year = date_obj.year
        round_raw = match.group(3)
        if round_raw.startswith('R'):
            round_num = round_raw[1:]  # remove the 'R'
        else:
            round_num = round_raw
        game_type = "HA" if round_raw.startswith("R") else "F"

        # Append structured game info
        games.append({
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
            "Date": date_obj.strftime('%Y-%m-%d'),
            "HT_Code": None,  # Placeholder
            "AT_Code": None   # Placeholder
        })

# Convert to DataFrame
df = pd.DataFrame(games)

# Save to CSV
df.to_csv('C:/Users/tyler/Documents/AFL_Coding/Python_Brownlow_Disposals/Downloaded_AFL_Tables/AFL_Game_Data.csv', index=False)
