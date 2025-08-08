"""
Scrapes historical data on harness racing results in Australia (horse finishes and track information).
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import sqlite3
from pathlib import Path
from datetime import datetime

def extract_race_table_data(table):
    """
    Extracts structured data for all runners in a single race from a race HTML table element.

    This function handles both historical races (with complete data) and upcoming races 
    (which may have missing or placeholder values). It parses key information such as 
    finishing position, horse name, prize money, barrier position, trainer/driver details, 
    margins, odds, and stewards' comments.

    Args:
        table: A table element containing race data.

    Returns:
        list[dict]: A list of dictionaries, each representing a runner with the following fields:
            - place (int): Finishing position.
            - horse_name (str): Name of the horse.
            - prize_money (int | None): Prize money earned, cleaned to an integer.
            - row_and_barrier (str): Starting row and barrier information.
            - tab_number (int): TAB number of the horse.
            - trainer (str): Trainers name.
            - driver (str): Drivers name.
            - margin (float | None): Margin behind the winner, in lengths.
            - starting_odds (float | None): Starting price odds.
            - stewards_comments (str): Commentary or remarks from race stewards.
            - post_race (bool): Flag indicating that this represents post-race data.
    
    Notes:
        - Races that have not yet run may return partial or inconsistent data.
        - Prints diagnostic information to help debug data inconsistencies.
    """
    html = table.inner_html()
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    # First row is header
    headers = [th.text.strip().lower() for th in rows[0].find_all("th")]

    has_form_column = "form" in headers # Races yet to run on the day have different table indexes
    print(f"📋 Headers: {headers}")
    print(f"🔎 'Form' column present? {'Yes' if has_form_column else 'No'}")

    race_data = []
    for row in rows[1:]:
        cols = row.find_all("td")

        if len(cols) < 10:
            continue  # Skip incomplete rows

        place = int(cols[0].text.strip())
        horse_name = cols[1].text.strip()

        def parse_prize_money(s):
            if not s:
                return None
            # Strip everything except digits
            cleaned = re.sub(r"[^\d]", "", s)
            if cleaned == "":
                return None
            return int(cleaned)
        prize_money_str = cols[2].text.strip()
        prize_money = parse_prize_money(prize_money_str)

        row_and_barrier = cols[4].text.strip()
        tab_number = int(cols[5].text.strip())
        trainer = cols[6].text.strip()
        driver = cols[7].text.strip()

        def parse_margin(margin_str):
            margin_str = margin_str.strip().upper()
            margin_map = {
                'HFHD': 0.05,
                'HD': 0.1,
                'NS': 0.03,
                'NK': 0.3,
                '1/2NK': 0.15,
                '1/2HD': 0.05,
                'SHFHD': 0.025,
            }

            if not margin_str:
                return 0.0  # Horse won
            elif margin_str in margin_map:
                return margin_map[margin_str]
            else:
                try:
                    return float(margin_str)
                except ValueError:
                    return None  # or raise an error or return 0.0 as fallback

        margin_str = cols[10].text.strip()
        margin = parse_margin(margin_str)

        def parse_odds(starting_odds_str):
            # Remove $ and non-digit/non-dot characters using regex
            cleaned = re.findall(r'\d+\.\d+|\d+', starting_odds_str)
            if cleaned:
                return float(cleaned[0])
            else:
                return None  # or some default value
        
        starting_odds_str = cols[11].text.strip()
        starting_odds = parse_odds(starting_odds_str)

        stewards_comments = cols[12].text.strip()

        post_race = True
        
        race_data.append({
        "place": place,
        "horse_name": horse_name,
        "prize_money": prize_money,
        "row_and_barrier": row_and_barrier,
        "tab_number": tab_number,
        "trainer": trainer,
        "driver": driver,
        "margin": margin,
        "starting_odds": starting_odds,
        "stewards_comments": stewards_comments,
        "post_race": post_race
        })

    return race_data

def extract_race_times_only(table_html, i, date):
    """
    Extracts and standardizes time-related metrics and metadata for a specific race from a race day table.

    Parses the race time splits (quarters, gross time, mile rate, lead time), track rating, and margins 
    between top finishers from the provided HTML table content. All time fields are converted to numeric 
    values (in seconds or float), and field names are normalized for consistency.

    Args:
        table_html (str): Raw HTML string of the race table (typically contains time-related info).
        i (int): The race number identifier on the card.
        date (str): The race date in "DDMMYY" format.

    Returns:
        dict: A dictionary with the following standardized fields:
            - date (datetime): Parsed date of the race.
            - race (int): Race number identifier.
            - track_rating (str): Track rating (e.g. "GOOD").
            - gross_time (float): Gross time of the race in seconds.
            - mile_rate (float): Mile rate of the race in seconds.
            - lead_time (float): Lead time in seconds.
            - first_quarter (float): Time for the first quarter (in seconds).
            - second_quarter (float): Time for the second quarter (in seconds).
            - third_quarter (float): Time for the third quarter (in seconds).
            - fourth_quarter (float): Time for the fourth quarter (in seconds).
            - margin_second (float | None): Margin from first to second place in lengths.
            - margin_third (float | None): Margin from second to third place in lengths.

    Notes:
        - Margins like "HD", "NK", or "NS" are mapped to fractional lengths.
        - Unexpected or missing margin formats are returned as `None`.
        - Assumes that the table contains all relevant rows with "key: value" formatted cells.
    """
    soup = BeautifulSoup(table_html, "html.parser")
    rows = soup.find_all("tr")

    race_times_data = {}

    # Race information
    date = datetime.strptime(date, "%d%m%y")
    race_times_data["date"] = date
    race_times_data["race"] = i

    for row in rows:
        cells = row.find_all("td")
        for cell in cells:
            text = cell.text.strip()
            if ':' in text:
                key, value = text.split(":", 1)
                race_times_data[key.strip()] = value.strip()

    def time_to_seconds(time_str):
        minutes, seconds, hundredths = map(int, time_str.split(':'))
        return minutes * 60 + seconds + hundredths / 100

    # In-place update
    race_times_data['Gross Time'] = time_to_seconds(race_times_data['Gross Time'])
    race_times_data['Mile Rate'] = time_to_seconds(race_times_data['Mile Rate'])
    race_times_data['Lead Time'] = float(race_times_data['Lead Time'])
    race_times_data['First Quarter'] = float(race_times_data['First Quarter'])
    race_times_data['Second Quarter'] = float(race_times_data['Second Quarter'])
    race_times_data['Third Quarter'] = float(race_times_data['Third Quarter'])
    race_times_data['Fourth Quarter'] = float(race_times_data['Fourth Quarter'])

    # Name change
    race_times_data['track_rating'] = race_times_data.pop('Track Rating')
    race_times_data['gross_time'] = race_times_data.pop('Gross Time')
    race_times_data['mile_rate'] = race_times_data.pop('Mile Rate')
    race_times_data['lead_time'] = race_times_data.pop('Lead Time') 
    race_times_data['first_quarter'] = race_times_data.pop('First Quarter')
    race_times_data['second_quarter'] = race_times_data.pop('Second Quarter')
    race_times_data['third_quarter'] = race_times_data.pop('Third Quarter')
    race_times_data['fourth_quarter'] = race_times_data.pop('Fourth Quarter')

    def update_margin_fields(race_times_data):
        margins_str = race_times_data.get('Margins', '').strip()
        parts = [m.strip() for m in margins_str.split('x')]

        def parse_margin(margin_str):
            margin_map = {
                'HFHD': 0.05,
                'SHFHD': 0.025,
                'HD': 0.1,
                'NS': 0.03,
                'NK': 0.3,
                '1/2NK': 0.15,
                '1/2HD': 0.05,
            }
            margin_str = margin_str.upper()
            if margin_str in margin_map:
                return margin_map[margin_str]
            try:
                return float(margin_str.replace('M', '').strip())
            except:
                return None

        race_times_data['margin_second'] = parse_margin(parts[0]) if len(parts) > 0 else None
        race_times_data['margin_third'] = parse_margin(parts[1]) if len(parts) > 1 else None

        # Delete the original 'Margins' key
        del race_times_data['Margins']

    update_margin_fields(race_times_data)
    
    return race_times_data

def generate_urls(start_date, end_date, base_url):
    """
    Generates a list of URLs based on a date range and base URL pattern.

    Each URL corresponds to a specific date within the range, formatted as "DDMMYY",
    and appended to the provided base URL. Useful for scraping or querying time-series
    data from date-specific web pages.

    Args:
        start_date (datetime): The start date (inclusive).
        end_date (datetime): The end date (inclusive).
        base_url (str): The base URL string to which the date will be appended.

    Returns:
        list[str]: A list of fully formed URLs covering the specified date range.
    """
    current = start_date
    urls = []
    while current <= end_date:
        date_str = current.strftime("%d%m%y")  # <-- DDMMYY format
        url = f"{base_url}{date_str}"
        urls.append(url)
        current += timedelta(days=1)
    return urls

def scrape_race_data_from_html(page, main_url):
    """
    Scrapes all horse-level and race-level data from a race day page on the target website.

    For each race:
        - Horse-level data (e.g., horse name, position, trainer) is extracted from tables containing 
          specific HTML patterns (like 'class="horse_name"').
        - Race-level data (e.g., times, margins, track rating) is extracted from tables with the 
          class "raceTimes".

    The extracted data is standardized with consistent date and track information to allow for downstream
    storage or analysis.

    Args:
        page (playwright.sync_api.Page): The Playwright page object for browser interaction.
        main_url (str): The URL of the race day page to scrape.

    Returns:
        tuple[list[dict], list[dict]]: 
            - A list of lists, where each inner list contains horse-level result dictionaries for one race.
            - A list of race-level result dictionaries containing time, margin, and metadata per race.

    Notes:
        - If the page fails to load, returns `(None, None)`.
        - Assumes race date and track code can be derived from the last 8 characters of the `main_url`.
    """
    print(f"🌐 Opening main page: {main_url}")
    
    # If website does not exist
    response = page.goto(main_url, timeout = 60000)
    if not response or response.status != 200:
        print(f"❌ Page returned status {response.status if response else 'None'}, skipping: {main_url}")
        return None, None

    frames = page.frames
    print(f"🧩 Found {len(frames)} frames total")

    # To track number of races
    result_tables = []

    # To store horse details
    all_race_results = []

    # To store race details
    all_race_times = []

    for frame in frames:
        try:
            frame_url = frame.url
            print(f"🔍 Checking frame: {frame_url}")

            frame.wait_for_selector("table", timeout=5000)
            tables = frame.query_selector_all("table")
            print(f"✅ Found {len(tables)} tables in this frame")

            for table in tables:
                html = table.inner_html()

                # Extracting horse details
                if 'class="horse_name"' in html:
                    print("🏁 Race result table found ✅")
                    result_tables.append(table)

                    race_results = extract_race_table_data(table)
                    all_race_results.append(race_results)

                    if race_results:
                        print(f"📄 Sample entry: {race_results[0]}")
            
            # Extracting race details
            race_times_tables = frame.query_selector_all("table.raceTimes")
            for i, race_times_table in enumerate(race_times_tables, 1):
                if race_times_table:
                    html = race_times_table.inner_html()
                    date = main_url[-6:]
                    race_times = extract_race_times_only(html, i, date)
                    print(f"\n📋 Race Times Table {i}")
                    print(race_times)
                    all_race_times.append(race_times)
                else:
                    print(f"❌ Race times table {i} not found.")

            # Normalize date outside, e.g., from main_url "010725" -> "2025-07-01"
            date_code = main_url[-6:]
            track = main_url[-8:-6]
            parsed_date = datetime.strptime(date_code, "%d%m%y").strftime("%Y-%m-%d")

            # Gives date and race information to use as keys across the two tables later
            for rt in all_race_times:
                rt["date"] = parsed_date  # ensure iso string
                rt["track"] = track
            for i, race in enumerate(all_race_results, 1):
                for horse in race:
                    horse["date"] = parsed_date
                    horse["race"] = i
                    horse["track"] = track

        except Exception as e:
            print(f"⛔ Error in frame: {e}")

    print(f"\n🎯 Total race result tables processed: {len(result_tables)}")

    return all_race_results, all_race_times

def scrape_multiple_race_days(urls):
    """
    Scrapes horse and race data from multiple URLs using Playwright.

    Launches a Chromium browser and iterates through the list of URLs,
    scraping horse results and race times from each page using the `scrape_race_data_from_html` function.

    Args:
        urls (list of str): List of URLs to scrape.

    Returns:
        tuple: Two lists:
            - master_horse_results: List of all horse result dictionaries from all URLs.
            - master_race_times: List of all race time dictionaries from all URLs.
    """
    master_horse_results = []
    master_race_times = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for url in urls:
            horse_results, race_times = scrape_race_data_from_html(page, url)

            # Only appending horse results that exist
            if horse_results:
                for race in horse_results:
                    master_horse_results.extend(race)

            # Only appending race results that exist
            if race_times:
                master_race_times.extend(race_times)

        browser.close()

    return master_horse_results, master_race_times

# --------------------------------------------------
# SQL Helper Functions

def init_db(db_path):
    """
    Initializes the SQLite database and creates the required tables if they do not exist.
    - `races`: Stores metadata for each race, including date, track, timing splits, and margins.
    - `horse_results`: Stores individual horse results for each race, including finishing position,
      odds, margins, and stewards’ comments.

    Both tables use appropriate constraints to enforce data integrity, including:
      - A unique constraint on (date, race_number, track) in `races`.
      - A foreign key relationship between `horse_results.race_id` and `races.race_id`.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        sqlite3.Connection: A live connection object to the initialized database.
    """
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS races (
        date TEXT NOT NULL,
        race_id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_number INTEGER NOT NULL,
        track TEXT NOT NULL,
        track_rating TEXT,
        gross_time REAL,
        mile_rate REAL,
        lead_time REAL,
        first_quarter REAL,
        second_quarter REAL,
        third_quarter REAL,
        fourth_quarter REAL,
        margin_second REAL,
        margin_third REAL,
        UNIQUE(date, race_number, track)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS horse_results (
        date TEXT NOT NULL,
        track TEXT NOT NULL,
        race_id INTEGER NOT NULL,
        horse_name TEXT NOT NULL,
        place INTEGER,
        tab_number INTEGER,
        trainer TEXT,
        driver TEXT,
        starting_odds REAL,
        margin REAL,
        prize_money REAL,
        stewards_comments TEXT,
        form TEXT,
        row_and_barrier TEXT,
        post_race INTEGER,
        FOREIGN KEY(race_id) REFERENCES races(race_id) ON DELETE CASCADE,
        UNIQUE(race_id, horse_name, date, track)
    )
    """)

    con.commit()
    return con

def upsert_race(con, race_time):
    """
    Inserts or updates a race entry in the 'races' table.

    If a race already exists with the same (date, race_number, track) combination,
    this function updates its timing and margin details. Otherwise, it inserts a new race.

    Args:
        con (sqlite3.Connection): Active connection to the SQLite database.
        race_time (dict): Dictionary containing race metadata.

    Returns:
        int: The `race_id` of the inserted or updated race.
    """
    cur = con.cursor()
    date = race_time["date"]
    race_number = race_time["race"]
    track = race_time.get("track")

    cur.execute("""
        INSERT INTO races (
            date, race_number, track, track_rating, gross_time, mile_rate, lead_time,
            first_quarter, second_quarter, third_quarter, fourth_quarter,
            margin_second, margin_third
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, race_number, track) DO UPDATE SET
            track_rating=excluded.track_rating,
            gross_time=excluded.gross_time,
            mile_rate=excluded.mile_rate,
            lead_time=excluded.lead_time,
            first_quarter=excluded.first_quarter,
            second_quarter=excluded.second_quarter,
            third_quarter=excluded.third_quarter,
            fourth_quarter=excluded.fourth_quarter,
            margin_second=excluded.margin_second,
            margin_third=excluded.margin_third
    """, (
        date,
        race_number,
        track,
        race_time.get("track_rating"),
        race_time.get("gross_time"),
        race_time.get("mile_rate"),
        race_time.get("lead_time"),
        race_time.get("first_quarter"),
        race_time.get("second_quarter"),
        race_time.get("third_quarter"),
        race_time.get("fourth_quarter"),
        race_time.get("margin_second"),
        race_time.get("margin_third"),
    ))
    con.commit()
    cur.execute("SELECT race_id FROM races WHERE date=? AND race_number=? AND track=?", (date, race_number, track))
    return cur.fetchone()[0]

def upsert_horse_result(con, horse, race_id):
    """
    Inserts or updates a horse result in the database.

    If the result already exists (based on race_id, horse_name, date, and track),
    it will be updated with the latest data. Otherwise, a new entry is inserted.

    Args:
        con (sqlite3.Connection): SQLite database connection.
        horse (dict): Dictionary of horse result data.
        race_id (int): Foreign key referencing the associated race.

    Returns:
        None
    """
    cur = con.cursor()
    cur.execute("""
        INSERT INTO horse_results (
            date, track, race_id, horse_name, place, tab_number, trainer, driver,
            starting_odds, margin, prize_money, stewards_comments, form,
            row_and_barrier, post_race
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(race_id, horse_name, date, track) DO UPDATE SET
            place=excluded.place,
            tab_number=excluded.tab_number,
            trainer=excluded.trainer,
            driver=excluded.driver,
            starting_odds=excluded.starting_odds,
            margin=excluded.margin,
            prize_money=excluded.prize_money,
            stewards_comments=excluded.stewards_comments,
            form=excluded.form,
            row_and_barrier=excluded.row_and_barrier,
            post_race=excluded.post_race
    """, (
        horse.get("date"),
        horse.get("track"),
        race_id,
        horse.get("horse_name"),
        horse.get("place"),
        horse.get("tab_number"),
        horse.get("trainer"),
        horse.get("driver"),
        horse.get("starting_odds"),
        horse.get("margin"),
        horse.get("prize_money"),
        horse.get("stewards_comments"),
        horse.get("form"),
        horse.get("row_and_barrier"),
        1 if horse.get("post_race") else 0,
    ))
    con.commit()

def ingest_to_sqlite(db_path, master_horse_results, master_race_times):
    """
    Ingests race and horse result data into a SQLite database.

    This function initialises the database (creating tables if they do not exist),
    then inserts or updates race-level and horse-level data. Races are inserted first,
    and each horse result is linked to its corresponding race via a foreign key.

    Args:
        db_path (str): Path to the SQLite database file.
        master_horse_results (list[dict]): A list of dictionaries containing horse-level data.
            Each dictionary must include a 'date' and 'race' (number) to match with races.
        master_race_times (list[dict]): A list of dictionaries containing race-level data.
            Each dictionary must include a 'date' and 'race' (number).

    Returns:
        sqlite3.Connection: An open SQLite connection for further querying or closing.
    """
    con = init_db(db_path)
    # Build a mapping from (date, race) -> race_id
    race_id_map = {}
    for rt in master_race_times:
        # Normalize date if it's a datetime
        if isinstance(rt.get("date"), datetime):
            rt["date"] = rt["date"].strftime("%Y-%m-%d")
        race_id = upsert_race(con, rt)
        race_id_map[(rt["date"], rt["race"])] = race_id

    # Insert horse results
    for horse in master_horse_results:
        date = horse.get("date")
        if isinstance(date, datetime):
            horse["date"] = date.strftime("%Y-%m-%d")
        race_number = horse.get("race")
        key = (horse.get("date"), race_number)
        race_id = race_id_map.get(key)
        if race_id is None:
            print(f"Warning: no race_times for horse entry {key}, skipping.")
            continue
        upsert_horse_result(con, horse, race_id)

    return con  # return connection if further queries needed

if __name__ == "__main__":
    # Setup - Gloucester Park - July 25 to July 26
    db_path = Path(r"C:\Users\tyler\Documents\CodingProjects\PuntBot\Database\race_results.db")
    start = "2025-07-25"
    end = "2025-07-26"
    base_url = "https://www.harness.org.au/racing/fields/race-fields/?mc=GP"

    # Generating urls
    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    urls = generate_urls(start_date, end_date, base_url)

    # Scraping each website
    master_horse_results, master_race_times = scrape_multiple_race_days(urls)
    
    # Inserting to database
    conn = ingest_to_sqlite(master_horse_results, master_race_times)
