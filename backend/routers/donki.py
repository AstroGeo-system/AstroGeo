import os
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import datetime
import math

router = APIRouter()

# Global cache so we don't parse the 300KB CSV on every tab click
_donki_data_cache = None

def get_donki_data():
    global _donki_data_cache
    if _donki_data_cache is not None:
        return _donki_data_cache

    # 4. ISRO Impacts (Static mock based on standard flare overlaps with 108 launch set)
    isro_impacts = [
        {"mission": "Chandrayaan-2", "date": "2019-07-22", "flare": "M2.1", "hours": "-14h", "outcome": "Successful"},
        {"mission": "PSLV-C49", "date": "2020-11-07", "flare": "M4.4", "hours": "+6h", "outcome": "Successful (Telemetry Noise Alert)"},
        {"mission": "GSLV-F10", "date": "2021-08-12", "flare": "X1.1", "hours": "-4h", "outcome": "Failed (Cryogenic Anomaly)"},
        {"mission": "Aditya-L1", "date": "2023-09-02", "flare": "M1.2", "hours": "+18h", "outcome": "Successful"}
    ]

    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'solar_events.csv')
    if not os.path.exists(csv_path):
        return {
            "live_status": None,
            "recent_feed": [],
            "timeline": [],
            "isro_impacts": isro_impacts
        }

    df = pd.read_csv(csv_path)
    
    # Sort chronological
    df = df.sort_values(by="datetime")
    
    # 1. Timeline for chart (aggregate max Kp per day or just list)
    # Filter only Geomagnetic storms for the Kp timeline chart, or fill missing.
    timeline = []
    storms = df[df["event_type"] == "geomagnetic_storm"]
    
    # Optional: Fill 0 for days without storms if we want a continuous chart, but recharts handles gaps ok
    # Just return the storm points for the timeline
    for _, row in storms.iterrows():
        try:
            kp = float(row["kp_index"])
            if not math.isnan(kp):
                timeline.append({
                    "date": str(row["date"]),
                    "kp_index": kp
                })
        except:
            pass

    # 2. Recent Events (last 10 chronological, descending)
    # Ensure May 10 2024 is prioritized ideally, but recent 10 should catch it if the db is recent.
    # Actually, the user specifically wants May 10 2024 to appear, so let's guarantee it's in the list.
    recent_df = df.sort_values(by="datetime", ascending=False)
    
    # Force include May 10 2024 event if it exists
    may10_event = recent_df[recent_df['date'].astype(str).str.contains('2024-05-10|2024-05-11', na=False)]
    
    # Get top 15, then filter
    top_events = recent_df.head(15).to_dict('records')
    
    recent_feed = []
    has_may10 = False
    
    for row in top_events:
        item = {
            "id": str(row.get("event_id", "")),
            "type": str(row.get("event_type", "")).replace("_", " ").title(),
            "date": str(row.get("date", "")),
            "time": str(row.get("datetime", "")),
            "intensity": str(row.get("intensity", "")),
            "description": str(row.get("description", ""))
        }
        if item["type"] == "Nan": continue
        
        # Check if this is the May 10 one
        if "2024-05-10" in item["date"] and "Kp9" in item["intensity"]:
            has_may10 = True
            
        recent_feed.append(item)
        if len(recent_feed) >= 10:
            break
            
    # If May 10 isn't in recent 10, hot-swap it with the last element
    if not has_may10 and not may10_event.empty:
        may_row = may10_event.iloc[0]
        recent_feed[-1] = {
            "id": str(may_row.get("event_id", "")),
            "type": "Geomagnetic Storm",
            "date": str(may_row.get("date", "")),
            "time": str(may_row.get("datetime", "")),
            "intensity": str(may_row.get("intensity", "")),
            "description": str(may_row.get("description", ""))
        }
    
    # Sort visually for chronological feed
    recent_feed.sort(key=lambda x: x["time"], reverse=True)

    # 3. Live Status (most recent overall)
    live_status = recent_feed[0] if recent_feed else None
    
    _donki_data_cache = {
        "live_status": live_status,
        "recent_feed": recent_feed,
        "timeline": timeline,
        "isro_impacts": isro_impacts
    }
    
    return _donki_data_cache


@router.get("/events")
async def get_solar_events():
    return get_donki_data()
