"""
Location Manager
Automatically adds new locations and fetches data
"""

import requests
from sqlalchemy import create_engine, text
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
N2YO_API_KEY = os.getenv('N2YO_API_KEY')

engine = create_engine(DATABASE_URL)

class LocationManager:
    
    def __init__(self):
        self.engine = engine
    
    def location_exists(self, location_name: str) -> bool:
        """Check if location already in database"""
        with self.engine.connect() as conn:
            conn.execute(text("SET search_path TO shared"))
            result = conn.execute(
                text("SELECT COUNT(*) FROM locations WHERE name ILIKE :name"),
                {'name': location_name}
            )
            count = result.scalar()
            return count > 0
    
    def get_coordinates_from_name(self, location_name: str) -> dict:
        """
        Geocode location name to lat/lon using free API
        Uses Nominatim (OpenStreetMap) - no API key needed
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_name,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'AstroGeo-SatelliteTracker/1.0'  # Required by Nominatim
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            result = data[0]
            return {
                'name': result.get('display_name', location_name),
                'latitude': float(result['lat']),
                'longitude': float(result['lon']),
                'country': result.get('address', {}).get('country', 'Unknown')
            }
            
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
    
    def add_location(self, location_name: str = None, latitude: float = None, longitude: float = None) -> dict:
        """
        Add new location to database
        
        Args:
            location_name: City name (will geocode if lat/lon not provided)
            latitude: Manual latitude (optional)
            longitude: Manual longitude (optional)
        
        Returns:
            dict with location_id, name, lat, lon
        """
        
        # Case 1: Name provided, need to geocode
        if location_name and (latitude is None or longitude is None):
            print(f"🔍 Geocoding '{location_name}'...")
            coords = self.get_coordinates_from_name(location_name)
            
            if not coords:
                raise ValueError(f"Could not find coordinates for '{location_name}'")
            
            location_name = coords['name']
            latitude = coords['latitude']
            longitude = coords['longitude']
            print(f"✅ Found: {location_name} ({latitude:.4f}, {longitude:.4f})")
        
        # Case 2: Lat/lon provided without name
        elif latitude and longitude and not location_name:
            location_name = f"Location_{latitude:.2f}_{longitude:.2f}"
        
        # Case 3: Neither provided
        elif not latitude or not longitude:
            raise ValueError("Must provide either location_name OR (latitude + longitude)")
        
        # Generate location_id
        location_id = location_name.lower().replace(' ', '_').replace(',', '')[:50] + '_001'
        
        # Check if already exists
        with self.engine.connect() as conn:
            conn.execute(text("SET search_path TO shared"))
            existing = conn.execute(
                text("SELECT location_id FROM locations WHERE location_id = :id"),
                {'id': location_id}
            ).fetchone()
            
            if existing:
                print(f"⚠️  Location '{location_name}' already exists with ID: {location_id}")
                return {
                    'location_id': location_id,
                    'name': location_name,
                    'latitude': latitude,
                    'longitude': longitude,
                    'already_existed': True
                }
        
        # Insert new location
        print(f"💾 Adding '{location_name}' to database...")
        
        with self.engine.connect() as conn:
            conn.execute(text("SET search_path TO shared"))
            conn.execute(text("""
                INSERT INTO locations (location_id, name, latitude, longitude, timezone, country)
                VALUES (:id, :name, :lat, :lon, 'Asia/Kolkata', :country)
            """), {
                'id': location_id,
                'name': location_name,
                'lat': latitude,
                'lon': longitude,
                'country': coords.get('country', 'Unknown') if 'coords' in locals() else 'Unknown'
            })
            conn.commit()
        
        print(f"✅ Location added: {location_id}")
        
        return {
            'location_id': location_id,
            'name': location_name,
            'latitude': latitude,
            'longitude': longitude,
            'already_existed': False
        }
    
    def fetch_data_for_location(self, location_id: str, latitude: float, longitude: float):
        """
        Fetch satellite passes and weather for new location
        """
        from satellite_data_fetcher import fetch_satellite_passes
        from weather_data_fetcher import fetch_weather_for_location
        
        print(f"\n📡 Fetching satellite passes for {location_id}...")
        
        # Priority satellites
        satellites = [
            {'id': 'ISS', 'norad_id': 25544},
            {'id': 'TIANGONG', 'norad_id': 48274},
            {'id': 'HUBBLE', 'norad_id': 20580}
        ]
        
        total_passes = 0
        for sat in satellites:
            passes = fetch_satellite_passes(
                sat['norad_id'],
                location_id,
                latitude,
                longitude,
                days=7
            )
            
            if passes:
                with self.engine.connect() as conn:
                    conn.execute(text("SET search_path TO satellite"))
                    for p in passes:
                        p['satellite_id'] = sat['id']
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
                
                print(f"  ✅ {sat['id']}: {len(passes)} passes")
                total_passes += len(passes)
        
        print(f"\n☁️  Fetching weather for {location_id}...")
        
        # Fetch weather (you'll need to adapt your weather fetcher)
        weather_result = fetch_weather_for_location({
            'location_id': location_id,
            'name': location_id,
            'latitude': latitude,
            'longitude': longitude
        })
        
        if weather_result['success']:
            print(f"  ✅ Weather data fetched")
        
        return {
            'satellite_passes': total_passes,
            'weather_fetched': weather_result['success']
        }
    
    def add_location_with_data(self, location_name: str = None, latitude: float = None, longitude: float = None) -> dict:
        """
        ONE-STEP: Add location and fetch all data automatically
        
        This is the main function you'll call from agents!
        """
        print("="*70)
        print(f"🌍 ADDING NEW LOCATION: {location_name or f'({latitude}, {longitude})'}")
        print("="*70)
        
        # Step 1: Add to database
        location = self.add_location(location_name, latitude, longitude)
        
        # Step 2: If it already existed, check if we need to refresh data
        if location['already_existed']:
            print("\n⚠️  Location already exists. Use refresh_location() to update data.")
            return location
        
        # Step 3: Fetch satellite and weather data
        data_result = self.fetch_data_for_location(
            location['location_id'],
            location['latitude'],
            location['longitude']
        )
        
        location.update(data_result)
        
        print("\n" + "="*70)
        print("✅ LOCATION SETUP COMPLETE!")
        print("="*70)
        print(f"Location ID: {location['location_id']}")
        print(f"Satellite passes: {location['satellite_passes']}")
        print(f"Weather data: {'✅' if location['weather_fetched'] else '❌'}")
        print("="*70)
        
        return location


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == '__main__':
    manager = LocationManager()
    
    # Example 1: Add by city name (auto-geocode)
    result = manager.add_location_with_data(location_name="Bangalore")
    
    