import asyncio
import httpx
from typing import Dict, List
from sqlalchemy import text
from backend.config import settings
from backend.routers.satellite_data_fetcher import fetch_n2yo_passes_live, engine


ISS_NORAD = 25544


class ISSService:
    """Handles ISS tracking.
    
    - Current position: Open-Notify (still live)
    - Pass predictions: N2YO live, falls back to PostgreSQL cache on failure
    """

    def __init__(self):
        self.iss_now_url = "http://api.open-notify.org/iss-now.json"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_current_position(self) -> Dict:
        """Get current ISS coordinates from Open-Notify (still live)."""
        try:
            response = await self.client.get(self.iss_now_url)
            response.raise_for_status()
            data = response.json()
            return {
                "latitude":  float(data["iss_position"]["latitude"]),
                "longitude": float(data["iss_position"]["longitude"]),
                "timestamp": data["timestamp"]
            }
        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch ISS position: {str(e)}")

    async def get_pass_times(
        self,
        lat: float,
        lon: float,
        passes: int = 5
    ) -> Dict:
        """
        Get upcoming ISS passes for a location.

        Strategy:
          1. Try N2YO live API (fetch_n2yo_passes_live)
             - Returns None  → API call failed (timeout, bad key, error body)
             - Returns []    → API succeeded, genuinely 0 passes in the window
             - Returns [..] → API succeeded, passes available
          2. Only fall back to PostgreSQL cache if None (actual failure)
             A valid "0 passes" result is returned as-is with data_source: "live"

        Returns a dict with:
          - passes: list of pass dicts
          - data_source: "live" | "cached" | "unavailable"
        """
        # ── Step 1: Try live N2YO fetch ────────────────────────────────────
        # fetch_n2yo_passes_live uses requests (sync) — run it in a thread pool
        # so it doesn't block the FastAPI async event loop.
        DAYS = 10
        MIN_EL = 10
        loop = asyncio.get_event_loop()
        live_result = await loop.run_in_executor(
            None,  # default ThreadPoolExecutor
            lambda: fetch_n2yo_passes_live(
                norad_id=ISS_NORAD,
                lat=lat,
                lon=lon,
                days=DAYS,
                min_elevation=MIN_EL
            )
        )

        if live_result is not None:
            # N2YO call succeeded (may be 0 passes — that's still "live")
            note = None
            if len(live_result) == 0:
                note = (
                    f"No visible ISS passes over your location in the next {DAYS} days "
                    f"(minimum elevation: {MIN_EL}°). "
                    "ISS visual passes require the station to be sunlit while your "
                    "location is in darkness — these windows are currently absent."
                )
            return {
                "passes":      live_result[:passes],
                "data_source": "live",
                "note":        note,
            }

        # ── Step 2: Fallback — nearest location in PostgreSQL cache ────────
        print("[ISSService] ⚠️  N2YO call failed — falling back to DB cache")
        try:
            cached = self._get_cached_passes(lat, lon, limit=passes)
            if cached:
                return {
                    "passes":      cached,
                    "data_source": "cached"
                }
        except Exception as e:
            print(f"[ISSService] ❌ DB fallback also failed: {e}")

        return {
            "passes":      [],
            "data_source": "unavailable"
        }

    def _get_cached_passes(self, lat: float, lon: float, limit: int = 5) -> List[Dict]:
        """
        Pull the nearest upcoming ISS passes from PostgreSQL.
        Finds the closest stored location to the requested coordinates.
        """
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO satellite, shared"))
            result = conn.execute(text("""
                SELECT
                    sp.rise_time,
                    sp.set_time,
                    sp.max_elevation_time,
                    sp.duration_seconds,
                    sp.max_elevation_deg,
                    sp.azimuth_rise_deg,
                    sp.azimuth_set_deg,
                    sp.magnitude,
                    sp.prediction_source,
                    l.name AS location_name,
                    -- Rough Euclidean distance to find nearest cached location
                    SQRT(POWER(l.latitude  - :lat, 2) +
                         POWER(l.longitude - :lon, 2)) AS distance
                FROM satellite.satellite_passes sp
                JOIN shared.locations l USING (location_id)
                WHERE sp.satellite_id = 'ISS'
                  AND sp.rise_time > NOW()
                ORDER BY distance ASC, sp.rise_time ASC
                LIMIT :limit
            """), {"lat": lat, "lon": lon, "limit": limit})

            rows = result.fetchall()

        passes = []
        for row in rows:
            r = dict(row._mapping)
            passes.append({
                "rise_time":              r["rise_time"].isoformat() if r["rise_time"] else None,
                "set_time":               r["set_time"].isoformat()  if r["set_time"]  else None,
                "max_elevation_time":     r["max_elevation_time"].isoformat() if r["max_elevation_time"] else None,
                "duration_seconds":       r["duration_seconds"],
                "max_elevation_deg":      r["max_elevation_deg"],
                "azimuth_rise_deg":       r["azimuth_rise_deg"],
                "azimuth_set_deg":        r["azimuth_set_deg"],
                "magnitude":              r["magnitude"],
                "prediction_source":      r["prediction_source"],
                "location_name":          r["location_name"],
            })
        return passes

    async def close(self):
        await self.client.aclose()


iss_service = ISSService()
