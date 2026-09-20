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

**4. Run the Pipeline**

Season year, feature columns, and file paths live in `config.py`. Scripts are numbered in run order:

```
python 01_scrape_games.py
python 02_scrape_players.py
python 03_scrape_advanced.py
python 04_merge.py
python 05_predict.py
```

The same steps are available as `python -m brownlow scrape-games` (then `scrape-players`, `scrape-advanced`, `merge`, `predict`), or `python -m brownlow all`.

`02_scrape_players.py` defaults to `PREDICT_YEAR` in `config.py`. Override with `--year 2024` if needed. `03_scrape_advanced.py` writes yearly Champion-style stats (`metres_gained`, `score_involvements`, `pressure_acts`, ...) under `data/raw/`. Optional ranker search on validation top-3 recall: `python 05_predict.py --tune`.

**5. View Output**

Predictions land in a season folder, for example `output/2025/`:

- `brownlow_2025_player_game_probabilities.csv`
- `brownlow_2025_heatmap_probability.csv`
- `brownlow_2025_heatmap_votes.csv`

**6. Tests**

```
python -m unittest tests.test_pipeline
```

## Key Components

- **Data Collection**: AFL Tables for box scores, plus Fryzigg / AFL.com.au for Champion-style advanced stats (metres gained, score involvements, intercepts, pressure acts).
- **Feature Engineering**: Creation of vote-influencing features such as player impact, disposals, efficiency, close-game context, and advanced stats.
- **Modeling**: XGBoost `rank:ndcg` treats official 0/1/2/3 votes as relevance grades and ranks players inside each match. Training uses earlier seasons; the latest labeled year is held out for early stopping.
- **Evaluation**: Walk-forward ranking metrics (top-3 recall, exact 3-2-1, best-on-ground, season Spearman) plus 3-2-1 heatmaps.
- **Output**: Final predictions for the configured Brownlow season are provided as CSVs (per-game probabilities and 3-2-1 vote heatmaps).

## Project Layout

- `01_scrape_games.py` … `05_predict.py`: Numbered entrypoints, in execution order.
- `config.py`: Season year, paths, feature list, team codes, and evaluation thresholds.
- `brownlow/`: Pipeline package (scrape, advanced, merge, features, model, predict, tune, CLI). Library modules are not numbered because those names would be invalid Python imports.
- `data/raw/`: Scraped player, game, and advanced-stat CSVs.
- `data/reference/brownlow_votes.csv`: Official 2017 and 2023 season tallies used when prior-year votes are missing.
- `data/processed/player_games.csv`: Merged player-game dataset used for training.
- `output/{year}/`: Season-specific prediction CSVs and heatmaps.
- `tests/`: Merge, feature, advanced-stat join, and 3-2-1 vote checks.

## Skills Demonstrated

- Python (Pandas, Scikit-learn, XGBoost)
- Data scraping and wrangling
- Model evaluation and feature importance analysis
- Real-world domain adaptation and output validation

## Status

Completed. Minor enhancements and testing ongoing.

---

*This project is part of a broader portfolio submitted for software engineering internship applications.*
