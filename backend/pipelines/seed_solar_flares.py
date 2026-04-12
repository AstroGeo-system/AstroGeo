# 09b_seed_solar_flares.py
# Pulls solar flare + geomagnetic storm data from NASA DONKI API
# Seeds SolarEvent nodes into Neo4j and connects them to
# existing Zone nodes by date and geographic region.
# Runtime: ~5 minutes. No auth needed (DEMO_KEY works).

import requests
import os
from datetime import datetime, timedelta
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Explicitly load backend/.env since we run from project root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# ── Config ────────────────────────────────────────────────────
NASA_API_KEY = os.getenv('NASA_API_KEY', 'DEMO_KEY')
BASE_URL     = "https://api.nasa.gov/DONKI"

# How far back to pull
START_DATE = "2018-01-01"
END_DATE   = datetime.now().strftime("%Y-%m-%d")

# Indian regions and their zones — maps to your existing Zone nodes
INDIA_REGIONS = {
    'North India':      ['Punjab', 'Haryana', 'Uttar Pradesh', 'Delhi'],
    'South India':      ['Tamil Nadu', 'Karnataka', 'Andhra Pradesh', 'Kerala'],
    'West India':       ['Maharashtra', 'Gujarat', 'Rajasthan'],
    'East India':       ['West Bengal', 'Odisha', 'Bihar', 'Jharkhand'],
    'Central India':    ['Madhya Pradesh', 'Chhattisgarh'],
    'Northeast India':  ['Assam', 'Manipur', 'Meghalaya'],
}

# Kp index threshold for "significant" geomagnetic storm
# Kp 5+ = minor storm, Kp 7+ = strong, Kp 9 = extreme
KP_THRESHOLD = 4  # capture moderate+ storms


# ── NASA DONKI API fetchers ───────────────────────────────────
def fetch_solar_flares():
    print("[DONKI] Fetching solar flares (chunked by year)...")
    url = f"{BASE_URL}/FLR"
    all_data = []
    start_y = int(START_DATE[:4])
    end_y = int(END_DATE[:4])
    
    for y in range(start_y, end_y + 1):
        s_date = f"{y}-01-01" if y == start_y else f"{y}-01-01"
        e_date = f"{y}-12-31" if y < end_y else END_DATE
        params = {"startDate": s_date, "endDate": e_date, "api_key": NASA_API_KEY}
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    all_data.extend(data)
        except Exception as e:
            print(f"  [!] Error fetching {y}: {e}")
            
    print(f"  → {len(all_data)} solar flares retrieved")
    return all_data

def fetch_geomagnetic_storms():
    print("[DONKI] Fetching geomagnetic storms (chunked by year)...")
    url = f"{BASE_URL}/GST"
    all_data = []
    start_y = int(START_DATE[:4])
    end_y = int(END_DATE[:4])
    
    for y in range(start_y, end_y + 1):
        s_date = f"{y}-01-01" if y == start_y else f"{y}-01-01"
        e_date = f"{y}-12-31" if y < end_y else END_DATE
        params = {"startDate": s_date, "endDate": e_date, "api_key": NASA_API_KEY}
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    all_data.extend(data)
        except Exception as e:
            print(f"  [!] Error fetching {y}: {e}")
            
    print(f"  → {len(all_data)} geomagnetic storms retrieved")
    return all_data

def fetch_radiation_belts():
    """
    Radiation Belt Enhancement events — directly affect
    satellite sensor degradation and GPS accuracy.
    """
    print("[DONKI] Fetching radiation belts (chunked by year)...")
    url = f"{BASE_URL}/RBE"
    all_data = []
    start_y = int(START_DATE[:4])
    end_y = int(END_DATE[:4])
    
    for y in range(start_y, end_y + 1):
        s_date = f"{y}-01-01" if y == start_y else f"{y}-01-01"
        e_date = f"{y}-12-31" if y < end_y else END_DATE
        params = {"startDate": s_date, "endDate": e_date, "api_key": NASA_API_KEY}
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    all_data.extend(data)
        except Exception as e:
            print(f"  [!] Error fetching {y}: {e}")
            
    print(f"  → {len(all_data)} radiation belt events retrieved")
    return all_data


# ── Parse events ──────────────────────────────────────────────
def parse_flares(raw_flares):
    parsed = []
    for f in raw_flares:
        try:
            parsed.append({
                'event_id':    f.get('flrID', ''),
                'event_type':  'solar_flare',
                'date':        f.get('beginTime', '')[:10],
                'datetime':    f.get('peakTime', f.get('beginTime', '')),
                'intensity':   f.get('classType', 'Unknown'),  # X1.5, M3.2 etc
                'source':      f.get('sourceLocation', 'Unknown'),
                'kp_index':    None,
                'description': f"Solar flare class {f.get('classType', '?')} "
                               f"from {f.get('sourceLocation', 'unknown location')}",
            })
        except Exception:
            continue
    return parsed


def parse_storms(raw_storms):
    parsed = []
    for s in raw_storms:
        try:
            # Get max Kp index across all KP data points
            kp_values = []
            for kp in s.get('allKpIndex', []):
                try:
                    kp_values.append(float(kp.get('kpIndex', 0)))
                except Exception:
                    pass

            max_kp = max(kp_values) if kp_values else 0

            if max_kp < KP_THRESHOLD:
                continue  # skip weak storms

            parsed.append({
                'event_id':    s.get('gstID', ''),
                'event_type':  'geomagnetic_storm',
                'date':        s.get('startTime', '')[:10],
                'datetime':    s.get('startTime', ''),
                'intensity':   f"Kp{max_kp}",
                'source':      'Magnetosphere',
                'kp_index':    max_kp,
                'description': f"Geomagnetic storm Kp={max_kp}. "
                               f"GPS degradation likely above Kp5. "
                               f"Smart irrigation risk above Kp6.",
            })
        except Exception:
            continue
    return parsed


# ── GPS disruption risk score ─────────────────────────────────
def compute_disruption_risk(event):
    """
    Returns a 0–1 risk score for smart irrigation disruption.
    Based on event type and intensity.
    """
    if event['event_type'] == 'geomagnetic_storm':
        kp = event.get('kp_index', 0) or 0
        # Kp 4=low risk, Kp 7=high risk, Kp 9=extreme
        return min(1.0, (kp - 4) / 5) if kp >= 4 else 0.1

    elif event['event_type'] == 'solar_flare':
        intensity = event.get('intensity', 'C1')
        # X class = highest, M = medium, C = low, B = negligible
        if intensity.startswith('X'):
            try:
                return min(1.0, 0.6 + float(intensity[1:]) * 0.04)
            except Exception:
                return 0.8
        elif intensity.startswith('M'):
            return 0.4
        elif intensity.startswith('C'):
            return 0.2
        return 0.1

    return 0.1


# ── Neo4j seeding ─────────────────────────────────────────────
def seed_neo4j(events):
    driver = GraphDatabase.driver(
        os.getenv('NEO4J_URI'),
        auth=(os.getenv('NEO4J_USERNAME', os.getenv('NEO4J_USER', 'neo4j')), os.getenv('NEO4J_PASSWORD'))
    )

    with driver.session() as session:

        # 1. Create SolarEvent nodes
        print("\n[Neo4j] Creating SolarEvent nodes...")
        for event in events:
            disruption_risk = compute_disruption_risk(event)
            session.run("""
                MERGE (e:SolarEvent {event_id: $event_id})
                SET e.event_type      = $event_type,
                    e.date            = $date,
                    e.datetime        = $datetime,
                    e.intensity       = $intensity,
                    e.kp_index        = $kp_index,
                    e.disruption_risk = $disruption_risk,
                    e.description     = $description,
                    e.source          = $source
            """, {**event, 'disruption_risk': disruption_risk})

        print(f"  → {len(events)} SolarEvent nodes created")

        # 2. Create Region nodes and connect to SolarEvents
        # All significant events affect all Indian regions
        # (geomagnetic storms are global, flares affect day-side)
        print("[Neo4j] Creating Region nodes and DISRUPTS edges...")

        for region_name, states in INDIA_REGIONS.items():
            session.run("""
                MERGE (r:Region {name: $name})
                SET r.states = $states,
                    r.country = 'India'
            """, {'name': region_name, 'states': states})

        # Connect storms to all regions (global effect)
        # Connect flares only to day-side (simplified: all India)
        for event in events:
            disruption_risk = compute_disruption_risk(event)
            if disruption_risk < 0.15:
                continue  # skip very weak events

            for region_name in INDIA_REGIONS.keys():
                session.run("""
                    MATCH (e:SolarEvent {event_id: $event_id})
                    MATCH (r:Region {name: $region_name})
                    MERGE (e)-[rel:DISRUPTS]->(r)
                    SET rel.risk_score = $risk_score,
                        rel.date       = $date
                """, {
                    'event_id':    event['event_id'],
                    'region_name': region_name,
                    'risk_score':  disruption_risk,
                    'date':        event['date'],
                })

        print("  → DISRUPTS edges created")

        # 3. Connect Regions to existing Zone nodes
        print("[Neo4j] Linking Regions to existing Zone nodes...")
        for region_name, states in INDIA_REGIONS.items():
            for state in states:
                session.run("""
                    MATCH (r:Region {name: $region_name})
                    MATCH (z:Zone)
                    WHERE z.name CONTAINS $state
                       OR z.state = $state
                    MERGE (z)-[:PART_OF]->(r)
                """, {
                    'region_name': region_name,
                    'state':       state,
                })

        print("  → Zone-Region links created")

        # 4. Verify — summary counts
        print("\n[Neo4j] Verification summary:")
        result = session.run("""
            MATCH (e:SolarEvent) RETURN count(e) AS solar_events
        """).single()
        print(f"  SolarEvent nodes:  {result['solar_events']}")

        result = session.run("""
            MATCH (r:Region) RETURN count(r) AS regions
        """).single()
        print(f"  Region nodes:      {result['regions']}")

        result = session.run("""
            MATCH ()-[r:DISRUPTS]->() RETURN count(r) AS edges
        """).single()
        print(f"  DISRUPTS edges:    {result['edges']}")

        result = session.run("""
            MATCH ()-[r:PART_OF]->() RETURN count(r) AS edges
        """).single()
        print(f"  PART_OF edges:     {result['edges']}")

        # 5. Test the key cross-domain query
        print("\n[Neo4j] Testing cross-domain query...")
        results = session.run("""
            MATCH (e:SolarEvent)-[:DISRUPTS]->(r:Region)
                  <-[:PART_OF]-(z:Zone)
                  -[:SHOWS_CHANGE]->(c:LandCoverChange)
            WHERE e.disruption_risk > 0.4
            RETURN e.date        AS event_date,
                   e.intensity   AS intensity,
                   e.event_type  AS type,
                   r.name        AS region,
                   z.name        AS zone,
                   c.type        AS land_change,
                   c.confidence  AS confidence
            ORDER BY e.disruption_risk DESC
            LIMIT 5
        """).data()

        if results:
            print("  ✅ Cross-domain query working! Sample result:")
            print(f"     {results[0]}")
        else:
            print("  ⚠️  No cross-domain results yet.")
            print("     This is OK if your Zone nodes don't have")
            print("     LandCoverChange edges yet — add them in Step 9.")

    driver.close()
    print("\n✅ Solar flare seeding complete!")


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("AstroGeo — Solar Flare Neo4j Seeder")
    print(f"Period: {START_DATE} → {END_DATE}")
    print("=" * 55)

    # Fetch
    raw_flares = fetch_solar_flares()
    raw_storms = fetch_geomagnetic_storms()

    # Parse
    flares = parse_flares(raw_flares)
    storms = parse_storms(raw_storms)
    all_events = flares + storms

    print(f"\nTotal events to seed: {len(all_events)}")
    print(f"  Solar flares:        {len(flares)}")
    print(f"  Geomagnetic storms:  {len(storms)}")

    if not all_events:
        print("No events found. Check your date range.")
        return

    # Seed Neo4j
    seed_neo4j(all_events)

    # Summary CSV for reference
    import pandas as pd
    df = pd.DataFrame(all_events)
    df['disruption_risk'] = df.apply(compute_disruption_risk, axis=1)
    df.to_csv('data/solar_events.csv', index=False)
    print(f"\n📄 CSV saved: data/solar_events.csv ({len(df)} rows)")


if __name__ == '__main__':
    # pip install requests neo4j pandas python-dotenv
    main()