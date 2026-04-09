"""
Centralized database query functions for all agents
"""

from sqlalchemy import create_engine, text
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

# ============================================================================
# SATELLITE QUERIES
# ============================================================================

def get_satellite_passes_tonight(location_name: str, hours_ahead: int = 24) -> list:
    """
    Get visible satellite passes for a location
    
    Returns list of dicts with pass details
    """
    query = text("""
        SELECT 
            satellite_id,
            TO_CHAR(rise_time, 'HH24:MI') as rise_time,
            TO_CHAR(set_time, 'HH24:MI') as set_time,
            max_elevation_deg,
            magnitude,
            cloud_cover_percent,
            weather_quality,
            combined_score,
            ROUND(hours_until_rise::numeric, 1) as hours_until,
            CASE 
                WHEN azimuth_rise_deg BETWEEN 0 AND 45 THEN 'North-Northeast'
                WHEN azimuth_rise_deg BETWEEN 45 AND 90 THEN 'Northeast'
                WHEN azimuth_rise_deg BETWEEN 90 AND 135 THEN 'East-Southeast'
                WHEN azimuth_rise_deg BETWEEN 135 AND 180 THEN 'South'
                WHEN azimuth_rise_deg BETWEEN 180 AND 225 THEN 'Southwest'
                WHEN azimuth_rise_deg BETWEEN 225 AND 270 THEN 'West'
                WHEN azimuth_rise_deg BETWEEN 270 AND 315 THEN 'Northwest'
                ELSE 'North'
            END as direction
        FROM satellite.tonights_visible_satellites
        WHERE location_name ILIKE :location
          AND hours_until_rise BETWEEN 0 AND :hours
        ORDER BY combined_score DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'location': f"%{location_name}%", 'hours': hours_ahead})
        return [dict(row._mapping) for row in result]


def get_weather_for_location(location_name: str) -> dict:
    """
    Get current weather and observation quality
    """
    query = text("""
        SELECT 
            temperature_celsius,
            cloud_cover_percent,
            weather_description,
            wind_speed_kmh,
            humidity_percent,
            quality_category,
            suitable_for_astronomy,
            quality_description,
            is_currently_night
        FROM weather.current_observation_conditions
        WHERE location_name ILIKE :location
        LIMIT 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'location': f"%{location_name}%"}).fetchone()
        return dict(result._mapping) if result else None


def get_best_viewing_location(satellite_id: str = 'ISS') -> dict:
    """
    Find which location has best viewing conditions tonight
    """
    query = text("""
        SELECT 
            location_name,
            TO_CHAR(rise_time, 'HH24:MI') as time,
            max_elevation_deg,
            magnitude,
            combined_score,
            cloud_cover_percent
        FROM satellite.tonights_visible_satellites
        WHERE satellite_id = :sat
          AND hours_until_rise BETWEEN 0 AND 12
        ORDER BY combined_score DESC
        LIMIT 1
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'sat': satellite_id}).fetchone()
        return dict(result._mapping) if result else None


def get_asteroid_by_id(asteroid_id: str) -> dict:
    """
    Get asteroid profile with ML predictions
    """
    query = text("""
        SELECT 
            asteroid_id,
            cluster as cluster_id,
            max_risk_score,
            risk_category,
            is_pha_candidate,
            total_approach_count,
            historical_frequency,
            estimated_diameter_km,
            discovery_era
        FROM asteroid_catalog.asteroid_profiles
        WHERE asteroid_id = :id
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'id': asteroid_id}).fetchone()
        return dict(result._mapping) if result else None


# ============================================================================
# LOCATION MANAGEMENT
# ============================================================================

def location_exists(location_name: str) -> bool:
    """Check if location is in database"""
    query = text("""
        SELECT COUNT(*) FROM shared.locations 
        WHERE name ILIKE :name
    """)
    
    with engine.connect() as conn:
        count = conn.execute(query, {'name': f"%{location_name}%"}).scalar()
        return count > 0