from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from backend.services.external.nasa_service import nasa_service

router = APIRouter(prefix="/api/v1/asteroids", tags=["Asteroids"])

@router.get("/close-approaches")
async def get_close_approaches(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    distance_max_au: Optional[float] = Query(None, gt=0, description="Max distance in AU"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get asteroid close approaches
    
    - **start_date**: Start date (YYYY-MM-DD), defaults to today
    - **end_date**: End date (YYYY-MM-DD), defaults to start_date + 7 days
    - **distance_max_au**: Filter asteroids closer than this distance
    - **limit**: Max results to return
    """
    try:
        # Default dates
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if not end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = (start + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Fetch from NASA
        asteroids = await nasa_service.get_close_approaches(
            start_date=start_date,
            end_date=end_date,
            distance_max_au=distance_max_au
        )
        
        # Apply limit
        asteroids = asteroids[:limit]
        
        return {
            "query": {
                "start_date": start_date,
                "end_date": end_date,
                "distance_filter_au": distance_max_au
            },
            "count": len(asteroids),
            "asteroids": asteroids
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{asteroid_id}")
async def get_asteroid_detail(asteroid_id: str):
    """Get detailed information about specific asteroid"""
    try:
        detail = await nasa_service.get_asteroid_detail(asteroid_id)
        return detail
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Asteroid not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))