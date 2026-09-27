"""Bulk scrape of harness.org.au race fields and results."""

from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup

import config
from puntbot.db import existing_form_meetings, ingest_form_rows, init_db
from puntbot.names import normalize_venue_name
from puntbot.tracks import code_to_betfair_name, venue_lookup

MARGIN_MAP = {
    "HFHD": 0.05,
    "HD": 0.1,
    "NS": 0.03,
    "NK": 0.3,
    "1/2NK": 0.15,
    "1/2HD": 0.05,
    "SHFHD": 0.025,
}

HEADER_ALIASES = {
    "place": {"place", "plc", "pl"},
    "horse_name": {"horse", "horse name", "runner"},
    "prize_money": {"prize", "prize money", "prize- money", "prize-money", "$", "prizemoney"},
    "form": {"form"},
    "row_and_barrier": {"row", "row and barrier", "row & br", "barrier", "row/barrier", "r/b"},
    "tab_number": {"tab", "tab #", "tab no", "no", "no.", "number", "#"},
    "trainer": {"trainer"},
    "driver": {"driver", "driver (c = concession)"},
    "margin": {"margin", "mgn", "mgn (m)"},
    "starting_odds": {"odds", "starting odds", "sp", "price", "starting price"},
    "stewards_comments": {
        "comments",
        "stewards",
        "stewards comments",
        "stewards' comments",
        "comment",
    },
}


def _header_index(headers: list[str]) -> dict[str, int]:
    index: dict[str, int] = {}
    lowered = [h.strip().lower() for h in headers]
    for field, aliases in HEADER_ALIASES.items():
        for pos, header in enumerate(lowered):
            if header in aliases:
                index[field] = pos
                break
    return index


def _cell(cols, index: dict[str, int], field: str) -> str:
    pos = index.get(field)
    if pos is None or pos >= len(cols):
        return ""
    return cols[pos].get_text(" ", strip=True)


def _parse_int(value: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", value or "")
    return int(cleaned) if cleaned else None


def _parse_prize_money(value: str) -> int | None:
    return _parse_int(value)


def parse_margin(margin_str: str | None) -> float | None:
    text = (margin_str or "").strip().upper()
    if not text:
        return 0.0
    if text in MARGIN_MAP:
        return MARGIN_MAP[text]
    try:
        return float(text.replace("M", "").strip())
    except ValueError:
        return None


def parse_odds(value: str) -> float | None:
    cleaned = re.findall(r"\d+\.\d+|\d+", value or "")
    return float(cleaned[0]) if cleaned else None


def time_to_seconds(time_str: str) -> float | None:
    parts = (time_str or "").split(":")
    try:
        if len(parts) == 3:
            minutes, seconds, frac = int(parts[0]), int(parts[1]), parts[2]
            divisor = 10 if len(frac) == 1 else 100
            return minutes * 60 + seconds + int(frac) / divisor
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        return float(time_str)
    except (TypeError, ValueError):
        return None


def _class_text(row, css_class: str) -> str:
    cell = row.find("td", class_=css_class)
    return cell.get_text(" ", strip=True) if cell else ""


def extract_race_table_data(table_html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(table_html, "html.parser")
    rows = soup.find_all("tr")
    if not rows:
        return []

    headers = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
    index = _header_index(headers)
    use_classes = bool(soup.find("td", class_="horse_name"))
    if "horse_name" not in index and not use_classes:
        return []

    race_data = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        if use_classes:
            horse_name = _class_text(row, "horse_name")
            number_cells = row.find_all("td", class_="horse_number")
            place = _parse_int(number_cells[0].get_text(" ", strip=True)) if number_cells else None
            tab_number = (
                _parse_int(number_cells[1].get_text(" ", strip=True)) if len(number_cells) > 1 else None
            )
            trainer = _class_text(row, "trainer")
            driver = _class_text(row, "driver")
            form = _class_text(row, "form") or None
            row_and_barrier = _class_text(row, "barrier") or None
            prize_money = _parse_prize_money(_class_text(row, "prizemoney"))
            margin = parse_margin(_class_text(row, "margin"))
            starting_odds = parse_odds(_class_text(row, "starting_price"))
            comments = _class_text(row, "stewards_comments") or None
        else:
            horse_name = _cell(cols, index, "horse_name")
            place = _parse_int(_cell(cols, index, "place"))
            tab_number = _parse_int(_cell(cols, index, "tab_number"))
            trainer = _cell(cols, index, "trainer")
            driver = _cell(cols, index, "driver")
            form = _cell(cols, index, "form") or None
            row_and_barrier = _cell(cols, index, "row_and_barrier") or None
            prize_money = _parse_prize_money(_cell(cols, index, "prize_money"))
            margin = parse_margin(_cell(cols, index, "margin"))
            starting_odds = parse_odds(_cell(cols, index, "starting_odds"))
            comments = _cell(cols, index, "stewards_comments") or None
        if not horse_name:
            continue
        race_data.append(
            {
                "place": place,
                "horse_name": horse_name,
                "prize_money": prize_money,
                "form": form,
                "row_and_barrier": row_and_barrier,
                "tab_number": tab_number,
                "trainer": trainer or None,
                "driver": driver or None,
                "margin": margin,
                "starting_odds": starting_odds,
                "stewards_comments": comments,
                "post_race": place is not None,
            }
        )
    return race_data


def extract_race_number(html: str, fallback: int) -> int:
    match = re.search(r"race\s*(\d+)", html, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return fallback


def extract_race_times_only(table_html: str, race_number: int, date_code: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(table_html, "html.parser")
    race_times_data: dict[str, Any] = {
        "date": datetime.strptime(date_code, "%d%m%y"),
        "race": race_number,
    }
    for row in soup.find_all("tr"):
        for cell in row.find_all("td"):
            text = cell.get_text(" ", strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                race_times_data[key.strip()] = value.strip()

    if "Gross Time" not in race_times_data:
        return {
            "date": race_times_data["date"],
            "race": race_number,
            "track_rating": race_times_data.get("Track Rating"),
        }

    mapped = {
        "track_rating": race_times_data.get("Track Rating"),
        "gross_time": time_to_seconds(str(race_times_data.get("Gross Time", ""))),
        "mile_rate": time_to_seconds(str(race_times_data.get("Mile Rate", ""))),
        "lead_time": _to_float(race_times_data.get("Lead Time")),
        "first_quarter": _to_float(race_times_data.get("First Quarter")),
        "second_quarter": _to_float(race_times_data.get("Second Quarter")),
        "third_quarter": _to_float(race_times_data.get("Third Quarter")),
        "fourth_quarter": _to_float(race_times_data.get("Fourth Quarter")),
        "date": race_times_data["date"],
        "race": race_number,
    }
    margins_str = str(race_times_data.get("Margins", "")).strip()
    parts = [part.strip() for part in margins_str.split("x") if part.strip()]
    mapped["margin_second"] = parse_margin(parts[0]) if parts else None
    mapped["margin_third"] = parse_margin(parts[1]) if len(parts) > 1 else None
    return mapped


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def generate_jobs(start_date: datetime, end_date: datetime, tracks: list[str]) -> list[tuple[str, str, str]]:
    jobs = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%d%m%y")
        iso = current.strftime("%Y-%m-%d")
        for track in tracks:
            url = f"{config.HARNESS_FIELDS_BASE}{track}{date_str}"
            jobs.append((url, iso, track.upper()))
        current += timedelta(days=1)
    return jobs


def generate_jobs_from_betfair(
    start_date: datetime,
    end_date: datetime,
    tracks: list[str],
    db_path=None,
) -> list[tuple[str, str, str]]:
    """Only visit meeting days that already exist in the Betfair table."""
    codes = [code.upper() for code in tracks]
    name_to_code = {code_to_betfair_name()[code]: code for code in codes if code in code_to_betfair_name()}
    aliases = venue_lookup()
    con = init_db(db_path)
    rows = con.execute(
        """
        SELECT DISTINCT meeting_date, track
        FROM betfair_runners
        WHERE meeting_date BETWEEN ? AND ?
          AND UPPER(COALESCE(state_code, '')) IN ('QLD','NSW','VIC','WA','SA','TAS','NT','ACT')
        """,
        (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
    ).fetchall()
    con.close()

    jobs = []
    wanted = set(codes)
    for row in rows:
        code = aliases.get(normalize_venue_name(row["track"]))
        if code is None:
            code = name_to_code.get(row["track"])
        if code not in wanted:
            continue
        date_str = datetime.strptime(row["meeting_date"], "%Y-%m-%d").strftime("%d%m%y")
        jobs.append((f"{config.HARNESS_FIELDS_BASE}{code}{date_str}", row["meeting_date"], code))
    jobs.sort(key=lambda item: (item[1], item[2]))
    return jobs


def parse_meeting_html(html: str, main_url: str) -> tuple[list[dict], list[dict]] | tuple[None, None]:
    if "Just a moment" in html or not html:
        return None, None

    meeting_code = main_url.split("mc=")[-1][:8]
    track = meeting_code[:2].upper()
    date_code = meeting_code[2:8]
    parsed_date = datetime.strptime(date_code, "%d%m%y").strftime("%Y-%m-%d")
    soup = BeautifulSoup(html, "html.parser")

    all_race_results: list[list[dict]] = []
    result_index = 0
    for table in soup.find_all("table"):
        table_html = str(table)
        if "horse_name" not in table_html:
            continue
        result_index += 1
        race_number = extract_race_number(table_html, result_index)
        runners = extract_race_table_data(table_html)
        if not runners:
            continue
        for horse in runners:
            horse["date"] = parsed_date
            horse["race"] = race_number
            horse["track"] = track
        all_race_results.append(runners)

    all_race_times: list[dict] = []
    for i, table in enumerate(soup.select("table.raceTimes"), 1):
        race_times = extract_race_times_only(str(table), extract_race_number(str(table), i), date_code)
        if race_times:
            race_times["date"] = parsed_date
            race_times["track"] = track
            all_race_times.append(race_times)

    if not all_race_results:
        return None, None

    existing = {(row["date"], row["race"], row["track"]) for row in all_race_times}
    for race in all_race_results:
        sample = race[0]
        key = (sample["date"], sample["race"], sample["track"])
        if key not in existing:
            all_race_times.append({"date": sample["date"], "race": sample["race"], "track": sample["track"]})
            existing.add(key)

    flat = [horse for race in all_race_results for horse in race]
    print(f"  {len(all_race_results)} races, {len(flat)} runners")
    return flat, all_race_times


def fetch_meeting_html(url: str) -> tuple[int | None, str]:
    import requests

    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=config.HARNESS_HTTP_HEADERS, timeout=30)
            return response.status_code, response.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_error)


def scrape_race_data_from_url(main_url: str) -> tuple[list[dict], list[dict]] | tuple[None, None]:
    print(f"Opening {main_url}")
    try:
        status, html = fetch_meeting_html(main_url)
    except Exception as exc:  # noqa: BLE001
        print(f"  skip after retries: {exc}")
        return None, None
    if status != 200:
        print(f"  skip status {status}")
        return None, None
    return parse_meeting_html(html, main_url)


def scrape_race_data_from_html(page, main_url: str) -> tuple[list[dict], list[dict]] | tuple[None, None]:
    print(f"Opening {main_url}")
    response = None
    last_error = None
    for attempt in range(3):
        try:
            response = page.goto(main_url, timeout=20000, wait_until="domcontentloaded")
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001 - retry network/timeouts
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if last_error:
        print(f"  skip after retries: {last_error}")
        return None, None
    if not response or response.status != 200:
        print(f"  skip status {response.status if response else 'None'}")
        return None, None
    return parse_meeting_html(page.content(), main_url)


def scrape_jobs(
    jobs: list[tuple[str, str, str]],
    headless: bool = True,
    delay: float = 0.4,
    use_browser: bool = False,
) -> tuple[list[dict], list[dict]]:
    master_horses: list[dict] = []
    master_times: list[dict] = []

    if not use_browser:
        for url, _iso, _track in jobs:
            horses, times = scrape_race_data_from_url(url)
            if horses:
                master_horses.extend(horses)
            if times:
                master_times.extend(times)
            time.sleep(delay)
        return master_horses, master_times

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        for url, _iso, _track in jobs:
            horses, times = scrape_race_data_from_html(page, url)
            if horses:
                master_horses.extend(horses)
            if times:
                master_times.extend(times)
            time.sleep(delay)
        browser.close()
    return master_horses, master_times


def run_scrape(
    start: str,
    end: str,
    tracks: list[str] | None = None,
    skip_existing: bool = True,
    headless: bool = True,
    delay: float = 0.4,
    from_betfair: bool = False,
    use_browser: bool = False,
) -> None:
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    track_codes = [code.upper() for code in (tracks or list(config.MAJOR_TRACK_CODES))]
    jobs = (
        generate_jobs_from_betfair(start_date, end_date, track_codes)
        if from_betfair
        else generate_jobs(start_date, end_date, track_codes)
    )

    con = init_db()
    if skip_existing:
        seen = existing_form_meetings(con)
        before = len(jobs)
        jobs = [job for job in jobs if (job[1], job[2]) not in seen]
        print(f"Skipping {before - len(jobs)} meetings already in the database")
    con.close()

    if not jobs:
        print("Nothing to scrape.")
        return

    print(f"Scraping {len(jobs)} meeting URLs ({start} to {end})")
    horses, times = scrape_jobs(jobs, headless=headless, delay=delay, use_browser=use_browser)
    con = init_db()
    ingest_form_rows(con, horses, times)
    con.close()
    print(f"Stored {len(horses)} horse rows and {len(times)} race rows in {config.DB_PATH}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Scrape harness.org.au form and results")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--tracks",
        default=",".join(config.MAJOR_TRACK_CODES),
        help="Comma-separated meeting codes (default: major AU tracks)",
    )
    parser.add_argument("--no-skip", action="store_true", help="Re-scrape meetings already in SQLite")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between pages in seconds")
    parser.add_argument(
        "--from-betfair",
        action="store_true",
        help="Only scrape date/track pairs that already exist in betfair_runners",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright instead of HTTP (www.harness.org.au may challenge this)",
    )
    args = parser.parse_args(argv)
    run_scrape(
        start=args.start,
        end=args.end,
        tracks=[part.strip() for part in args.tracks.split(",") if part.strip()],
        skip_existing=not args.no_skip,
        headless=not args.headed,
        delay=args.delay,
        from_betfair=args.from_betfair,
        use_browser=args.browser,
    )
