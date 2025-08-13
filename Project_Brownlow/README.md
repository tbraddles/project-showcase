# Project Brownlow

A machine learning project aimed at predicting the 2025 AFL Brownlow Medal votes using tree-based regression models. The project emphasizes high-quality feature engineering, model interpretability, and real-world alignment with market predictions.

## Overview

The Brownlow Medal is awarded to the best and fairest AFL player each season, with votes cast after each match. This project attempts to predict vote outcomes using structured historical data and ensemble machine learning methods.

## Usage

**1. Clone the Repository**
```
git clone https://github.com/tbraddles/project-showcase.git
cd project-showcase/Project_Brownlow
```

**2. Create and Activate a Virtual Environment**

On Windows:
```
python -m venv venv
venv\Scripts\activate
```

**3. Install Required Dependencies**
```
pip install -r requirements.txt
```

**4. Run the Pipeline Scripts in Order**

4-1. Scrape game-level data:
```
python game_data_scraper.py
```

4-2. Scrape player-level data (set to scrape 2025 data):
```
python player_data_scraper.py
```

4-3. Merge and clean the AFL data:
```
python merge_afl_data.py
```

4-4. Generate Brownlow predictions:
```
python brownlow_predictor.py
```

**5. View Output**

- Navigate to the `output` folder to see the generated prediction files.

## Key Components

- **Data Collection**: A custom Python scraper to gather match-level data and player statistics.
- **Feature Engineering**: Creation of vote-influencing features such as player impact, disposals, efficiency, and team performance.
- **Modeling**: Applied tree-based regression models (e.g., Random Forest, XGBoost) to estimate vote likelihood on a per-game basis.
- **Evaluation**: Model outputs were validated against historical voting patterns.
- **Output**: Final predictions for the 2025 Brownlow Medal winner are provided in Excel format.

## Files Included

- `player_data_scraper.py`: Downloads and cleans per-player stats from AFL Tables across a given season.
- `game_data_scraper.py`: Collects and standardises game-level scores and metadata.
- `merge_afl_data.py`: Merges player and game data into a unified dataset with contextual features.
- `brownlow_predictor.py`: Builds and evaluates the Brownlow prediction model; generates per-match and overall vote predictions.
- `xgb_tuning_utils.py`: Contains hyperparameter tuning logic using GridSearchCV for optimizing XGBoost performance.
- `Master_AFL_Data.csv`: Cleaned and combined dataset used for model training and analysis.
- `Current_Predictions.xlsx`: Formatted output of current Brownlow predictions based on most recent data.

## Directories

- `afl_tables/`: Raw scraped CSVs for player and match data (organized by year).
- `output/`: Generated prediction outputs, including season vote tallies, match-by-match vote heatmaps, and Excel exports.

## Skills Demonstrated

- Python (Pandas, Scikit-learn, XGBoost)
- Data scraping and wrangling
- Model evaluation and feature importance analysis
- Real-world domain adaptation and output validation

## Status

✅ Completed. Minor enhancements and testing ongoing.

---

*This project is part of a broader portfolio submitted for software engineering internship applications.*
