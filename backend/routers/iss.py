from fastapi import APIRouter, HTTPException
from backend.services.external.iss_service import iss_service

router = APIRouter(prefix="/api/v1/iss", tags=["ISS Tracking"])


@router.get("/position")
async def get_iss_position():
    """Get current ISS position (live from Open-Notify)."""
    try:
        position = await iss_service.get_current_position()
        return position
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/passes")
async def get_iss_passes(
    lat: float,
    lon: float,
    passes: int = 5
):
    """
    Get upcoming ISS pass predictions for a location.

    - Tries N2YO live API first (fresh data)
    - Falls back to PostgreSQL cache if live fails

    Response includes:
      - passes: list of upcoming passes
      - data_source: "live" | "cached" | "unavailable"
    """
    try:
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Invalid latitude")
        if not (-180 <= lon <= 180):
            raise HTTPException(status_code=400, detail="Invalid longitude")

        result = await iss_service.get_pass_times(lat, lon, passes=passes)

        return {
            "location":    {"lat": lat, "lon": lon},
            "data_source": result["data_source"],
            "note":        result.get("note"),
            "passes":      result["passes"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))