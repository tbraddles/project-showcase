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

# Setup - Gloucester Park - July 25 to July 26
DB_PATH = Path(r"C:\Users\tyler\Documents\CodingProjects\PuntBot\Database\race_results.db")
filename = r"C:\Users\tyler\Documents\CodingProjects\PuntBot\Database\scraped_results.csv"
start = "2025-07-25"
end = "2025-07-26"
base_url = "https://www.harness.org.au/racing/fields/race-fields/?mc=GP"

def extract_race_table_data(table):
    """
    Extracts all individual horse details for a given race. 
    # Note this can handle races yet to occur but the data collected will not be in the same form as historical data
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
    Extracts all race details for a given race day. 
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
    Generates a url list to examine.
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
    Scrapes all horse and race data for a given url. 
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

# --------------------------------------------------
# SQL Helper Functions

def init_db(db_path=DB_PATH):
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

# --------------------------------------------------
# After scraping, ingest into SQLite:
# master_race_times: list of race-time dicts
# master_horse_results: list of races (each is list of horse dicts), 
#                       each horse dict must have 'date' and 'race' fields

def ingest_to_sqlite(master_race_times, master_horse_results):
    con = init_db()
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


# --------------------------------------------------
# Running scraping and ingesting into SQL

# Generating dates
start_date = datetime.strptime(start, "%Y-%m-%d")
end_date = datetime.strptime(end, "%Y-%m-%d")
urls = generate_urls(start_date, end_date, base_url)

# Scraping each website
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    master_horse_results = []
    master_race_times = []
    for url in urls:
        horse_results, race_times = scrape_race_data_from_html(page, url)
        # Only appending horse results that exist
        if horse_results:
            for race in horse_results:
                master_horse_results.extend(race)
          # Only appending horse results that exist
        if race_times:
            master_race_times.extend(race_times)      
    browser.close()

conn = ingest_to_sqlite(master_race_times, master_horse_results)