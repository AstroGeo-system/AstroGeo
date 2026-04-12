# backend/pipelines/03_scrape_launches.py
# Scrapes ISRO launch history from the Satish Dhawan Space Centre
# Wikipedia page — the only source with confirmed ERA5 weather coverage.
# Column layout (all tables): 0=#  1=date  2=vehicle  3=serial  4=result  5=notes

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

SDSC_URL   = "https://en.wikipedia.org/wiki/List_of_Satish_Dhawan_Space_Centre_launches"
OUTPUT_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'data', 'launches', 'launch_history.csv'
)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)


def _strip_refs(text: str) -> str:
    """Remove Wikipedia footnote markers like [1], [Note 2], etc."""
    return re.sub(r'\[.*?\]', '', text).strip()


def _parse_outcome(text: str) -> str:
    text = text.lower()
    if 'failure' in text:
        return 'failure'
    elif 'partial' in text:
        return 'failure'   # treat partial as failure for binary label
    else:
        return 'success'


def scrape_sdsc_launches():
    print("[Scraper] Fetching SDSC launch history from Wikipedia...")
    headers = {'User-Agent': 'Mozilla/5.0 AstroGeo-Research-Bot/1.0'}
    resp    = requests.get(SDSC_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    launches = []
    tables   = soup.find_all('table', {'class': 'wikitable'})
    print(f"  → Found {len(tables)} wikitables")

    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # skip header
            cells = row.find_all(['td', 'th'])
            if len(cells) < 5:
                continue
            try:
                date_raw    = _strip_refs(cells[1].get_text(separator=' ', strip=True))
                vehicle_raw = _strip_refs(cells[2].get_text(strip=True))
                result_raw  = _strip_refs(cells[4].get_text(strip=True))
                notes_raw   = _strip_refs(cells[5].get_text(strip=True)) if len(cells) > 5 else ''

                # Extract mission name from notes (first part before comma/slash)
                mission = notes_raw.split(',')[0].split('/')[0].strip() or vehicle_raw

                # Clean date — take first date-like portion before newline or parenthesis
                date_str = date_raw.split('\n')[0].split('(')[0].strip()

                launches.append({
                    'mission':     mission[:120],
                    'vehicle':     vehicle_raw,
                    'date':        date_str,
                    'launch_site': 'Sriharikota',
                    'agency':      'ISRO',
                    'outcome':     _parse_outcome(result_raw),
                })
            except Exception:
                continue

    print(f"  → {len(launches)} raw rows extracted")
    return launches


def clean_and_save(launches):
    df = pd.DataFrame(launches)

    df['date']    = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    df            = df.dropna(subset=['date'])
    df            = df[df['date'].dt.year >= 1980]
    df['year']    = df['date'].dt.year
    df['month']   = df['date'].dt.month
    df['success'] = (df['outcome'] == 'success').astype(int)

    df = df.drop_duplicates(subset=['mission', 'date'])
    df = df.reset_index(drop=True)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved {len(df)} launches → {OUTPUT_CSV}")
    print(f"   Success rate: {df['success'].mean():.1%}")
    print(f"   Date range:   {df['date'].min().date()} → {df['date'].max().date()}")
    return df


def save_to_postgres(df):
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
    )
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS launch_history (
            id          SERIAL PRIMARY KEY,
            mission     TEXT,
            vehicle     TEXT,
            date        DATE,
            year        INTEGER,
            month       INTEGER,
            launch_site TEXT,
            agency      TEXT,
            outcome     TEXT,
            success     INTEGER,
            UNIQUE(mission, date)
        )
    """)

    rows = [
        (
            row['mission'], row['vehicle'], row['date'].date(),
            int(row['year']), int(row['month']),
            row['launch_site'], row['agency'],
            row['outcome'], int(row['success']),
        )
        for _, row in df.iterrows()
    ]

    execute_values(cur, """
        INSERT INTO launch_history
            (mission, vehicle, date, year, month,
             launch_site, agency, outcome, success)
        VALUES %s
        ON CONFLICT (mission, date) DO NOTHING
    """, rows)

    conn.commit()
    cur.close()
    conn.close()
    print(f"  [DB] Saved {len(rows)} rows to launch_history")


if __name__ == '__main__':
    launches = scrape_sdsc_launches()
    df       = clean_and_save(launches)
    save_to_postgres(df)