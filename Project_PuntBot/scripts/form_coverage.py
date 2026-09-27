"""Print form coverage and remaining Betfair-backed scrape jobs."""

from datetime import datetime

import config
from puntbot.db import init_db
from puntbot.scrape_form import generate_jobs_from_betfair
from puntbot.db import existing_form_meetings


CORE_TRACKS = ["GP", "MX", "PC", "AP", "RE"]


def main() -> None:
    con = init_db()
    print("horse_results", con.execute("select count(*) from horse_results").fetchone()[0])
    print("races", con.execute("select count(*) from races").fetchone()[0])
    print("date_range", con.execute("select min(date), max(date) from races").fetchone())
    print("meetings", con.execute("select count(*) from (select distinct date, track from races)").fetchone()[0])
    print("by_track")
    for row in con.execute(
        "select track, min(date), max(date), count(*) from races group by track order by track"
    ):
        print(" ", tuple(row))
    seen = existing_form_meetings(con)
    con.close()

    for label, start, end in (
        ("2023_2025", datetime(2023, 1, 1), datetime(2025, 12, 31)),
        ("2026", datetime(2026, 1, 1), datetime(2026, 8, 31)),
    ):
        jobs = generate_jobs_from_betfair(start, end, CORE_TRACKS)
        remaining = [job for job in jobs if (job[1], job[2]) not in seen]
        print(f"core_jobs_{label}", len(jobs))
        print(f"already_stored_{label}", len(jobs) - len(remaining))
        print(f"remaining_{label}", len(remaining))
        if remaining:
            print(f"first_remaining_{label}", remaining[0])
            print(f"last_remaining_{label}", remaining[-1])


if __name__ == "__main__":
    main()
