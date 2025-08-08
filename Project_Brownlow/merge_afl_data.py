"""
merge_afl_data.py

Loads multiple years of AFL player data and game scores, cleans and merges them
to create a master dataset combining player stats with corresponding game info.
Saves the merged dataset to CSV.
"""

import pandas as pd
from pathlib import Path

def merge_afl_data(base_dir: str, player_years: list[int], output_file: str):
    """
    Loads multiple years of AFL player and game data, cleans and merges them into a single master dataset.

    The function:
    - Reads player stats CSV files for the specified years from the 'afl_tables' subdirectory of the base directory.
    - Filters out finals rounds and standardizes text columns.
    - Loads and filters game score data from the same 'afl_tables' directory.
    - Maps full team names to standardized team codes.
    - Merges player data with game scores twice to handle cases where player's team is home or away.
    - Resolves overlapping columns from the two merges into single columns.
    - Saves the combined dataset as a CSV file to the specified output path.

    Parameters:
        base_dir (str): Path to the base directory containing the 'afl_tables' folder with data files.
        player_years (list[int]): List of years for which to load player stats CSV files.
        output_file (str): Filename (with extension) for saving the merged dataset CSV, saved inside base_dir.

    The output CSV contains a master dataset combining player statistics with corresponding match context,
    suitable for further analysis.
    """
    BASE_DIR = Path(base_dir)
    tables_dir = BASE_DIR / "afl_tables"
    output_dir = BASE_DIR
    finals_rounds = ['QF', 'EF', 'SF', 'PF', 'GF']

    # Load and prepare player data
    player_dfs = []
    for year in player_years:
        df = pd.read_csv(tables_dir / f"{year}_AFL_Player_Data.csv")
        df['Year'] = year
        player_dfs.append(df)
    data_players = pd.concat(player_dfs, ignore_index=True)

    # Remove finals rounds & convert Round to int
    data_players = data_players[~data_players['Round'].isin(finals_rounds)].copy()
    data_players['Round'] = data_players['Round'].astype(int)

    # Clean relevant columns
    for col in ['Team', 'Opponent', 'Player']:
        if col in data_players.columns:
            data_players[col] = data_players[col].astype(str).str.strip().str.upper()

    # Load scores data
    data_scores = pd.read_csv(tables_dir / "AFL_Game_Data.csv")

    # Filter scores data for home and away games after 2009
    data_scores = data_scores[(data_scores['Year'] > 2009) & (data_scores['Game_Type'] == 'HA')].copy()

    # Map full team names to codes
    team_code_map = {
        'Adelaide': 'AD', 'Brisbane Lions': 'BL', 'Carlton': 'CA', 'Collingwood': 'CW',
        'Essendon': 'ES', 'Fremantle': 'FR', 'Geelong': 'GE', 'Gold Coast': 'GC',
        'GW Sydney': 'GW', 'Hawthorn': 'HW', 'Melbourne': 'ME', 'North Melbourne': 'NM',
        'Port Adelaide': 'PA', 'Richmond': 'RI', 'St Kilda': 'SK', 'Sydney': 'SY',
        'West Coast': 'WC', 'Western Bulldogs': 'WB'
    }

    data_scores['HT_Code'] = data_scores['Home_Team'].map(team_code_map).str.upper()
    data_scores['AT_Code'] = data_scores['Away_Team'].map(team_code_map).str.upper()

    # Clean codes and teams columns
    for col in ['HT_Code', 'AT_Code', 'Home_Team', 'Away_Team']:
        if col in data_scores.columns:
            data_scores[col] = data_scores[col].astype(str).str.strip().str.upper()

    # Ensure Year and Round are int
    for df in [data_players, data_scores]:
        for col in ['Year', 'Round']:
            if col in df.columns:
                df[col] = df[col].astype(int)

    # First merge: Player's Team = Home Team, Opponent = Away Team
    merged_data = pd.merge(
        data_players, data_scores,
        how='left',
        left_on=['Round', 'Team', 'Opponent', 'Year'],
        right_on=['Round', 'HT_Code', 'AT_Code', 'Year'],
        suffixes=('', '_score')
    )

    # Second merge: Player's Team = Away Team, Opponent = Home Team
    merged_data_v1 = pd.merge(
        merged_data, data_scores,
        how='left',
        left_on=['Round', 'Opponent', 'Team', 'Year'],
        right_on=['Round', 'HT_Code', 'AT_Code', 'Year'],
        suffixes=('_x', '_y')
    )

    # Function to pick values from _x if not null, else from _y
    def choose_column(row, col):
        if pd.isna(row[f'{col}_x']):
            return row[f'{col}_y']
        else:
            return row[f'{col}_x']

    # List all columns to resolve (adjust this based on actual data_scores columns)
    cols_to_resolve = [
        'Game ID', 'Game_Type', 'Day', 'Home_Team', 'Away_Team', 'Venue', 'Time_Category',
        'Home_Goals', 'Home_Behinds', 'Home_Total', 'Away_Goals', 'Away_Behinds', 'Away_Total',
        'After_Game', 'Date', 'Time', 'HT_Code', 'AT_Code'
    ]

    # Apply resolution for each column
    for col in cols_to_resolve:
        if f'{col}_x' in merged_data_v1.columns and f'{col}_y' in merged_data_v1.columns:
            merged_data_v1[col] = merged_data_v1.apply(lambda row: choose_column(row, col), axis=1)

    # Drop all columns with _x and _y suffixes
    merged_data_v2 = merged_data_v1.drop(
        columns=[col for col in merged_data_v1.columns if col.endswith('_x') or col.endswith('_y')]
    )

    # Save final merged dataset
    merged_data_v2.to_csv(output_dir / output_file, index=False)
    print(f"Merge complete and saved to {output_file}")

if __name__ == "__main__":
    base_dir = "C:/Users/tyler/Documents/CodingProjects/Brownlow"
    output_file = "Master_AFL_Data.csv"
    player_years = [2018, 2019, 2020, 2021, 2022, 2024, 2025] # Note 2023 have incomplete data
    merge_afl_data(base_dir, player_years, output_file)