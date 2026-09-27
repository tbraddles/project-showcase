import sqlite3

import pandas as pd

import config

con = sqlite3.connect(config.DB_PATH)
dates = pd.read_sql("select meeting_date from betfair_runners", con)["meeting_date"]
con.close()
parsed = pd.to_datetime(dates)
months = parsed[parsed.dt.year == 2025].dt.to_period("M").value_counts().sort_index()
print(months.to_string())
print("total_2025", int(months.sum()))
