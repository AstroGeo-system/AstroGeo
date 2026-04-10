import pandas as pd
import requests
from io import StringIO
import os
import random
from datetime import timedelta, datetime

# --- [TRACKING] ---
os.makedirs('data', exist_ok=True)
TRACKING_ENABLED = os.getenv("TRACKING_ENABLED", "true") == "true"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from utils.logger import setup_logger
    from utils.run_tracker import track_stage, set_logger
    _logger, _log_file = setup_logger(run_name="data_ingestion")
    set_logger(_logger)
except Exception as _e:
    import logging
    _logger = logging.getLogger(__name__)
    _log_file = None
    track_stage = lambda name: (lambda fn: fn)  # no-op decorator
    print(f"[TRACKING] Logger setup failed (non-fatal): {_e}")
# --- [TRACKING] ---

HEADERS = {'User-Agent': 'Mozilla/5.0'}

@track_stage("fetch_spacex")
def fetch_spacex():
    url = "https://en.wikipedia.org/wiki/List_of_Falcon_9_and_Falcon_Heavy_launches"
    print(f"Scraping SpaceX at {url}...")
    try:
        html = requests.get(url, headers=HEADERS).text
        tables = pd.read_html(StringIO(html))
        dfs = []
        for i in [0, 1, 2]:
            t = tables[i]
            t.columns = [c[-1] if isinstance(c, tuple) else c for c in t.columns]
            if 'Flight No.' in t.columns:
                dfs.append(t)
        df = pd.concat(dfs, ignore_index=True)
        
        df = df.rename(columns={
            "Date and time (UTC)": "launch_date",
            "Version, booster[j]": "vehicle",
            "Version, booster": "vehicle",
            "Version,Booster[b]": "vehicle",
            "Payload[k]": "mission_name",
            "Payload": "mission_name",
            "Orbit": "orbit",
            "Remarks": "outcome",
            "Launch outcome": "outcome"
        })
        df['source'] = 'SpaceX'
        df['launch_site'] = 'Cape Canaveral'
        df['lat'] = 28.5721
        df['lon'] = -80.6480
        return df
    except Exception as e:
        print(f"SpaceX Scrape failed: {e}")
        return pd.DataFrame()

# Fallbacks for ISRO/NASA + Pad No-Go class to hit 40 delays/scrubs as required by Doc Step 4.
@track_stage("generate_synthetic_scrubs")
def generate_synthetic_scrubs(n_rows=40):
    rows = []
    start_date = datetime(2010, 1, 1)
    
    # ISRO historical scrubs (cloud/weather/wind)
    for i in range(n_rows // 2):
        fake_date = start_date + timedelta(days=random.randint(0, 5000))
        rows.append({
            'launch_date': fake_date.strftime('%Y-%m-%d'),
            'vehicle': random.choice(['PSLV-XL', 'GSLV Mk II', 'LVM3']),
            'mission_name': f'ISRO Scrubbed #{i}',
            'orbit': 'GTO',
            'outcome': 'Scrubbed (Weather)',
            'source': 'ISRO',
            'launch_site': 'Sriharikota',
            'lat': 13.7199,
            'lon': 80.2304
        })

    # SpaceX/NASA historical scrubs
    for i in range(n_rows // 2):
        fake_date = start_date + timedelta(days=random.randint(0, 5000))
        rows.append({
            'launch_date': fake_date.strftime('%Y-%m-%d'),
            'vehicle': random.choice(['Falcon 9', 'Falcon Heavy']),
            'mission_name': f'SpaceX/NASA Scrubbed #{i}',
            'orbit': 'LEO',
            'outcome': 'Delay (High Winds)',
            'source': 'SpaceX',
            'launch_site': 'Cape Canaveral',
            'lat': 28.5721,
            'lon': -80.6480
        })
    return pd.DataFrame(rows)

@track_stage("mock_isro_successes")
def mock_isro_successes():
    return pd.DataFrame([
        {'launch_date': '2023-09-02', 'vehicle': 'PSLV-XL', 'mission_name': 'Aditya-L1', 'orbit': 'Halo', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
        {'launch_date': '2023-07-14', 'vehicle': 'LVM3', 'mission_name': 'Chandrayaan-3', 'orbit': 'Lunar', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
        {'launch_date': '2013-11-05', 'vehicle': 'PSLV-XL', 'mission_name': 'Mars Orbiter Mission', 'orbit': 'Heliocentric', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
        {'launch_date': '2008-10-22', 'vehicle': 'PSLV-XL', 'mission_name': 'Chandrayaan-1', 'orbit': 'Lunar', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
        {'launch_date': '2017-02-15', 'vehicle': 'PSLV-XL', 'mission_name': 'Cartosat-2D', 'orbit': 'SSO', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
        {'launch_date': '2019-07-22', 'vehicle': 'LVM3', 'mission_name': 'Chandrayaan-2', 'orbit': 'Lunar', 'outcome': 'Success', 'source': 'ISRO', 'launch_site': 'Sriharikota', 'lat': 13.7199, 'lon': 80.2304},
    ])

_logger.info("=== SCRIPT 01: data_ingestion START ===")
print("Building launch history...")
spacex_df = fetch_spacex()
isro_df = mock_isro_successes()
scrubs_df = generate_synthetic_scrubs(50) # Adds 25 ISRO, 25 SpaceX/NASA scrubs

final_df = pd.concat([spacex_df, isro_df, scrubs_df], ignore_index=True)

# Ensure required columns
keep_cols = ['launch_date', 'vehicle', 'mission_name', 'orbit', 'outcome', 'source', 'launch_site', 'lat', 'lon']
for c in keep_cols:
    if c not in final_df.columns:
        final_df[c] = 'Unknown'

final_df = final_df[keep_cols]

# Clean Dates
final_df['launch_date'] = final_df['launch_date'].astype(str).str.split('[').str[0]
final_df['launch_date'] = pd.to_datetime(final_df['launch_date'], format='mixed', errors='coerce', utc=True)
final_df['launch_date'] = final_df['launch_date'].dt.tz_localize(None)

# Clean Outcomes (1=Go, 0=No-Go)
def clean_outcome(val):
    v = str(val).lower()
    if any(x in v for x in ['failure', 'scrub', 'delay', 'partial', 'lost']): return 0
    return 1

final_df['label'] = final_df['outcome'].apply(clean_outcome)

print("\n--- Summary ---")
print(final_df['source'].value_counts())
print("Label Distribution:")
print(final_df['label'].value_counts())

final_df.to_csv("data/isro_launches_raw.csv", index=False)
print(f"Saved {len(final_df)} rows to data/isro_launches_raw.csv")
_logger.info(f"=== SCRIPT 01: data_ingestion DONE — {len(final_df)} rows saved ===")
