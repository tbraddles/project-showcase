from datetime import datetime

from puntbot.db import existing_form_meetings, init_db
from puntbot.scrape_form import generate_jobs_from_betfair

CORE = ["GP", "MX", "PC", "AP", "RE"]
con = init_db()
seen = existing_form_meetings(con)
con.close()
jobs = generate_jobs_from_betfair(datetime(2025, 1, 1), datetime(2025, 7, 31), CORE)
left = [j for j in jobs if (j[1], j[2]) not in seen]
print("h1_2025_jobs", len(jobs), "remaining", len(left))
if left:
    print("first", left[0])
    print("last", left[-1])
