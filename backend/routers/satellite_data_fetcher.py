from __future__ import annotations
import requests
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from backend.config import settings

DATABASE_URL = settings.DATABASE_URL
N2YO_API_KEY = settings.N2YO_API_KEY  # Read from settings (not raw os.getenv)

engine = create_engine(DATABASE_URL)

# High-priority satellites to track
PRIORITY_SATELLITES = [
    {'id': 'ISS',      'norad_id': 25544, 'name': 'International Space Station'},
    {'id': 'TIANGONG', 'norad_id': 48274, 'name': 'Tiangong Space Station'},
    {'id': 'HUBBLE',   'norad_id': 20580, 'name': 'Hubble Space Telescope'},
]

# ─────────────────────────────────────────────────────────────────────────────
# Shared live-fetch function — single source of truth for all N2YO calls
# ─────────────────────────────────────────────────────────────────────────────

def fetch_n2yo_passes_live(
    norad_id: int,
    lat: float,
    lon: float,
    days: int = 5,
    min_elevation: int = 10
) -> list[dict] | None:
    """
    Fetch visible satellite passes directly from N2YO API.

    N2YO URL format:
      /visualpasses/{norad}/{lat}/{lon}/{alt}/{days}/{min_el}/?apiKey={key}

    Rules:
      - days must be 1–10 (N2YO hard limit)
      - min_elevation 0–90 degrees; use 10 for typical viewing
      - apiKey must be appended directly to the URL, not as a params dict
        (avoids any URL-encoding issues with special characters in the key)
    """
    days = min(days, 10)  # N2YO hard cap

    url = (
        f"https://api.n2yo.com/rest/v1/satellite/visualpasses"
        f"/{norad_id}/{lat}/{lon}/0/{days}/{min_elevation}/"
        f"?apiKey={N2YO_API_KEY}"
    )

    print(f"\n[N2YO] Fetching live passes:")
    print(f"       URL → {url}\n")

    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()

        print(f"[N2YO] Raw response keys: {list(data.keys())}")
        print(f"[N2YO] Raw response: {data}")

        # N2YO returns HTTP 200 even on errors — always check the body
        if "error" in data:
            print(f"[N2YO] ❌ API error: {data['error']}")
            return None  # Signals fetch failure to caller

        # 'passes' key absent means 0 passes (valid successful response)
        if "passes" not in data:
            passes_count = data.get("info", {}).get("passescount", 0)
            print(f"[N2YO] ✅ Call succeeded — {passes_count} visual passes in window (no night-time illuminated passes)")
            return []  # Successful call, genuinely 0 passes

        passes_raw = data["passes"]
        print(f"[N2YO] ✅ {len(passes_raw)} pass(es) returned for NORAD {norad_id}")

        passes = []
        for p in passes_raw:
            passes.append({
                'rise_time':              datetime.fromtimestamp(p['startUTC'], tz=timezone.utc),
                'set_time':               datetime.fromtimestamp(p['endUTC'],   tz=timezone.utc),
                'max_elevation_time':     datetime.fromtimestamp(p['maxUTC'],   tz=timezone.utc),
                'duration_seconds':       p['duration'],
                'max_elevation_deg':      p['maxEl'],
                'azimuth_rise_deg':       p['startAz'],
                'azimuth_set_deg':        p['endAz'],
                'azimuth_max_elevation_deg': p['maxAz'],
                'magnitude':              p.get('mag'),
                'prediction_source':      'N2YO_LIVE',
            })

        return passes

    except requests.exceptions.Timeout:
        print(f"[N2YO] ⏱ Timeout fetching passes for NORAD {norad_id}")
        return None  # Signals fetch failure to caller
    except Exception as e:
        print(f"[N2YO] ❌ Exception: {e}")
        return None  # Signals fetch failure to caller


# ─────────────────────────────────────────────────────────────────────────────
# Pre-fetch job — fetches and caches passes for all satellites × locations
# ─────────────────────────────────────────────────────────────────────────────

def fetch_satellite_passes(satellite_norad_id, location_id, lat, lon, days=10):
    """
    Wrapper around fetch_n2yo_passes_live for the batch pre-fetch job.
    Adds location_id to each pass dict for DB insertion.
    Returns [] if the N2YO call fails (None guard).
    """
    passes = fetch_n2yo_passes_live(satellite_norad_id, lat, lon, days=days)
    if passes is None:
        return []   # API call failed — nothing to insert
    for p in passes:
        p['satellite_id'] = None   # Set by caller
        p['location_id']  = location_id
    return passes


def load_passes_for_all_locations():
    """
    Fetch and store passes for all satellites × all locations in the DB.
    """
    print("=" * 70)
    print("SATELLITE AGENT: FETCHING PASS PREDICTIONS")
    print("=" * 70)

    with engine.connect() as conn:
        conn.execute(text("SET search_path TO shared"))
        result = conn.execute(text(
            "SELECT location_id, name, latitude, longitude FROM locations"
        ))
        locations = [dict(row._mapping) for row in result]

    print(f"\nLocations: {len(locations)}")
    print(f"Satellites: {len(PRIORITY_SATELLITES)}\n")

    total_passes = 0

    for satellite in PRIORITY_SATELLITES:
        print(f"\n📡 {satellite['name']} (NORAD {satellite['norad_id']})")

        for location in locations:
            print(f"  → {location['name']}...", end=" ")

            passes = fetch_satellite_passes(
                satellite['norad_id'],
                location['location_id'],
                location['latitude'],
                location['longitude']
            )

            if passes:
                with engine.connect() as conn:
                    conn.execute(text("SET search_path TO satellite"))

                    for p in passes:
                        p['satellite_id'] = satellite['id']

                        conn.execute(text("""
                            INSERT INTO satellite_passes (
                                satellite_id, location_id,
                                rise_time, set_time, max_elevation_time,
                                duration_seconds, max_elevation_deg,
                                azimuth_rise_deg, azimuth_set_deg, azimuth_max_elevation_deg,
                                magnitude, prediction_source
                            ) VALUES (
                                :satellite_id, :location_id,
                                :rise_time, :set_time, :max_elevation_time,
                                :duration_seconds, :max_elevation_deg,
                                :azimuth_rise_deg, :azimuth_set_deg, :azimuth_max_elevation_deg,
                                :magnitude, :prediction_source
                            )
                            ON CONFLICT (satellite_id, location_id, rise_time) DO NOTHING
                        """), p)

                    conn.commit()

                print(f"✅ {len(passes)} passes")
                total_passes += len(passes)
            else:
                print("❌ No passes")

    print(f"\n{'=' * 70}")
    print(f"✅ TOTAL PASSES LOADED: {total_passes}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    load_passes_for_all_locations()