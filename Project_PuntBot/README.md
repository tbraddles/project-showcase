# Project PuntBot

An automated trading bot designed for Australian harness racing markets. This project integrates data scraping, SQLite-based database architecture, and algorithmic decision logic to support real-time execution and evaluation of betting strategies.

## Overview

The goal of PuntBot is to simulate and evaluate algorithmic betting strategies on live horse harness racing data. 

## Usage

**1. Clone the Repository**
```
git clone https://github.com/tbraddles/project-showcase.git
cd project-showcase/Project_PuntBot
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

**4. Run the script**
```
python puntbot_scraper.py
```

## Key Components

- **Data Pipeline**: 
  - Web scraping of race market and runner data from Betfair.
  - Conversion and parsing of compressed `.bz2` stream data.
  - Storage in a structured local SQLite database.

- **Database Architecture**:
  - Designed a lightweight schema to efficiently store race metadata, runner-level metrics, and market snapshots.
  - Includes historical results for outcome validation.

- **Strategy Simulation**:
  - Ongoing work on algorithmic optimisation to evaluate betting logic based on market efficiency, volatility, and price movement patterns.

## Files Included

- `puntbot_scraper.py`: Extracts and processes detailed historical harness racing data from harness.org.au. Also manages data insertion for the local SQLite database.
- `racing_data.xlsx`: Sample output of processed and structured racing data.

## Skills Demonstrated

- Python (requests, sqlite3, pandas)
- Data scraping and cleaning
- Database design and querying (SQL/SQLite)
- Automation and scheduled data collection
- Early-stage algorithm development for real-time systems

## Status

🚧 In progress — data architecture and extraction scripts complete; strategy engine under active development.

---

*This project is part of a broader portfolio submitted for software engineering internship applications.*
