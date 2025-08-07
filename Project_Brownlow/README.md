# Project Brownlow

A machine learning project aimed at predicting the 2025 AFL Brownlow Medal votes using tree-based regression models. The project emphasizes high-quality feature engineering, model interpretability, and real-world alignment with market predictions.

## Overview

The Brownlow Medal is awarded to the best and fairest AFL player each season, with votes cast after each match. This project attempts to predict vote outcomes using structured historical data and ensemble machine learning methods.

## Key Components

- **Data Collection**: A custom Python scraper to gather match-level data and player statistics.
- **Feature Engineering**: Creation of vote-influencing features such as player impact, disposals, efficiency, and team performance.
- **Modeling**: Applied tree-based regression models (e.g., Random Forest, XGBoost) to estimate vote likelihood on a per-game basis.
- **Evaluation**: Model outputs were validated against historical voting patterns.
- **Output**: Final predictions for the 2025 Brownlow Medal winner are provided in Excel format.

## Sample Files Included (Note not all files included)

- `brownlow_scraper_games.py`: Script used to collect and clean match data.
- `brownlow_model.py`: Main model training and evaluation script.
- `brownlow_predictions.xlsx`: Final 2025 predictions exported to Excel, broadly aligned with current betting markets.

## Skills Demonstrated

- Python (Pandas, Scikit-learn, XGBoost)
- Data scraping and wrangling
- Model evaluation and feature importance analysis
- Real-world domain adaptation and output validation

## Status

✅ Completed. Minor enhancements and testing ongoing.

---

*This project is part of a broader portfolio submitted for software engineering internship applications.*
