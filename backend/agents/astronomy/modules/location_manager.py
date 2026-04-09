"""
Location Manager - Hybrid Approach
Pre-populated cities + Dynamic additions
"""

from sqlalchemy import create_engine, text
import requests
from datetime import datetime
import os
import sys

# Add project root to path for standalone execution
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 4 levels: modules -> astronomy -> agents -> backend -> root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.config import settings
    DATABASE_URL = settings.DATABASE_URL
    N2YO_API_KEY = settings.N2YO_API_KEY
except ImportError:
    # Fallback to env vars if not running in app context and finding config fails
    # But ideally we want to find the config
    from dotenv import load_dotenv
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL')
    N2YO_API_KEY = os.getenv('N2YO_API_KEY')

engine = create_engine(DATABASE_URL)

class LocationManager:
    """
    Manages locations with hybrid approach:
    - 30 pre-populated cities (instant access)
    - Dynamic addition for new cities (auto-geocode + fetch data)
    """
    
    def __init__(self):
        self.engine = engine
        self.geocoding_cache = {}
    
    def exists(self, location_name: str) -> bool:
        """
        Check if location exists in database
        
        Args:
            location_name: City name (case-insensitive, fuzzy match)
        
        Returns:
            True if found, False otherwise
        """
        query = text("""
            SELECT COUNT(*) 
            FROM shared.locations 
            WHERE name ILIKE :name
        """)
        
        with self.engine.connect() as conn:
            count = conn.execute(query, {'name': f"%{location_name}%"}).scalar()
            return count > 0
    
    def get_location_id(self, location_name: str) -> str:
        """
        Get location_id for a given city name
        
        Returns:
            location_id or None if not found
        """
        query = text("""
            SELECT location_id, name 
            FROM shared.locations 
            WHERE name ILIKE :name
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'name': f"%{location_name}%"}).fetchone()
            return result[0] if result else None
    
    def geocode(self, location_name: str) -> dict:
        """
        Geocode location name to coordinates using Nominatim
        
        Args:
            location_name: City name to geocode
        
        Returns:
            {'name': str, 'latitude': float, 'longitude': float, 'country': str}
            or None if not found
        """
        # Check cache first
        if location_name in self.geocoding_cache:
            print(f"  ℹ️  Using cached geocoding for {location_name}")
            return self.geocoding_cache[location_name]
        
        # Nominatim API (OpenStreetMap)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{location_name}, India",  # Bias towards India
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'AstroGeo/1.0 (Astronomical Observation Planner)'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                print(f"  ❌ Could not geocode '{location_name}'")
                return None
            
            result = data[0]
            address = result.get('address', {})
            
            geocoded = {
                'name': result.get('display_name', location_name),
                'short_name': address.get('city') or address.get('town') or address.get('village') or location_name,
                'latitude': float(result['lat']),
                'longitude': float(result['lon']),
                'country': address.get('country', 'Unknown'),
                'region': address.get('state', 'Unknown')
            }
            
            # Cache it
            self.geocoding_cache[location_name] = geocoded
            
            print(f"  ✅ Geocoded: {geocoded['short_name']} ({geocoded['latitude']:.4f}, {geocoded['longitude']:.4f})")
            return geocoded
            
        except Exception as e:
            print(f"  ❌ Geocoding error: {e}")
            return None
    
    def add_to_database(self, location_data: dict) -> str:
        """
        Add new location to database
        
        Args:
            location_data: Dict from geocode() function
        
        Returns:
            location_id of new location
        """
        # Generate location_id
        short_name = location_data['short_name'].lower().replace(' ', '_')
        location_id = f"{short_name}_user_001"
        
        # Check if already exists (edge case: concurrent requests)
        if self.exists(location_data['short_name']):
            print(f"  ⚠️  {location_data['short_name']} already exists")
            return self.get_location_id(location_data['short_name'])
        
        query = text("""
            INSERT INTO shared.locations (
                location_id, name, latitude, longitude, 
                timezone, country, region, created_at
            ) VALUES (
                :id, :name, :lat, :lon, 
                'Asia/Kolkata', :country, :region, NOW()
            )
            ON CONFLICT (location_id) DO NOTHING
            RETURNING location_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'id': location_id,
                'name': location_data['short_name'],
                'lat': location_data['latitude'],
                'lon': location_data['longitude'],
                'country': location_data['country'],
                'region': location_data['region']
            })
            conn.commit()
            
            print(f"  💾 Added to database: {location_id}")
            return location_id
    
    def fetch_satellite_passes(self, location_id: str, latitude: float, longitude: float):
        """
        Fetch satellite passes for new location
        Uses N2YO API
        """
        print(f"  📡 Fetching satellite passes...")
        
        satellites = [
            {'id': 'ISS', 'norad_id': 25544},
            {'id': 'TIANGONG', 'norad_id': 48274},
            {'id': 'HUBBLE', 'norad_id': 20580}
        ]
        
        total_passes = 0
        
        for sat in satellites:
            url = f"https://api.n2yo.com/rest/v1/satellite/visualpasses/{sat['norad_id']}/{latitude}/{longitude}/0/7/300/"
            params = {'apiKey': N2YO_API_KEY}
            
            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if 'passes' not in data:
                    continue
                
                passes = data['passes']
                
                # Insert into database
                with self.engine.connect() as conn:
                    conn.execute(text("SET search_path TO satellite"))
                    
                    for p in passes:
                        conn.execute(text("""
                            INSERT INTO satellite_passes (
                                satellite_id, location_id,
                                rise_time, set_time, max_elevation_time,
                                duration_seconds, max_elevation_deg,
                                azimuth_rise_deg, azimuth_set_deg, azimuth_max_elevation_deg,
                                magnitude, prediction_source
                            ) VALUES (
                                :sat_id, :loc_id,
                                to_timestamp(:rise_utc), to_timestamp(:set_utc), to_timestamp(:max_utc),
                                :duration, :max_el,
                                :az_rise, :az_set, :az_max,
                                :mag, 'N2YO'
                            )
                            ON CONFLICT (satellite_id, location_id, rise_time) DO NOTHING
                        """), {
                            'sat_id': sat['id'],
                            'loc_id': location_id,
                            'rise_utc': p['startUTC'],
                            'set_utc': p['endUTC'],
                            'max_utc': p['maxUTC'],
                            'duration': p['duration'],
                            'max_el': p['maxEl'],
                            'az_rise': p['startAz'],
                            'az_set': p['endAz'],
                            'az_max': p['maxAz'],
                            'mag': p.get('mag')
                        })
                    
                    conn.commit()
                
                print(f"    ✅ {sat['id']}: {len(passes)} passes")
                total_passes += len(passes)
                
            except Exception as e:
                print(f"    ❌ {sat['id']}: Failed ({e})")
        
        return total_passes
    
    def fetch_weather(self, location_id: str, latitude: float, longitude: float):
        """
        Fetch weather data for new location
        Uses Open-Meteo API
        """
        print(f"  ☁️  Fetching weather data...")
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': 'temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m',
            'hourly': 'temperature_2m,cloud_cover,precipitation_probability',
            'daily': 'temperature_2m_max,temperature_2m_min,sunrise,sunset',
            'timezone': 'Asia/Kolkata',
            'forecast_days': 7
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current = data.get('current', {})
            
            # Insert current conditions
            with self.engine.connect() as conn:
                conn.execute(text("SET search_path TO weather"))
                
                conn.execute(text("""
                    INSERT INTO current_conditions (
                        location_id, observed_at,
                        temperature_celsius, humidity_percent, cloud_cover_percent,
                        precipitation_mm, wind_speed_kmh,
                        data_source
                    ) VALUES (
                        :loc_id, NOW(),
                        :temp, :humidity, :clouds,
                        :precip, :wind,
                        'Open-Meteo'
                    )
                """), {
                    'loc_id': location_id,
                    'temp': current.get('temperature_2m'),
                    'humidity': current.get('relative_humidity_2m'),
                    'clouds': current.get('cloud_cover', 0),
                    'precip': current.get('precipitation', 0),
                    'wind': current.get('wind_speed_10m')
                })
                
                conn.commit()
            
            print(f"    ✅ Weather data fetched")
            return True
            
        except Exception as e:
            print(f"    ❌ Weather fetch failed: {e}")
            return False
    
    def ensure_location_exists(self, location_name: str) -> dict:
        """
        MAIN FUNCTION: Ensure location exists, add if not
        
        This is the function AstronomyAgent will call!
        
        Args:
            location_name: City name (e.g., "Guwahati", "Shimla")
        
        Returns:
            {
                'location_id': str,
                'name': str,
                'latitude': float,
                'longitude': float,
                'was_added': bool,  # True if just added, False if existed
                'satellite_passes': int,
                'weather_fetched': bool
            }
        """
        print(f"\n{'='*70}")
        print(f"📍 LOCATION CHECK: {location_name}")
        print(f"{'='*70}")
        
        # Step 1: Check if exists
        if self.exists(location_name):
            location_id = self.get_location_id(location_name)
            print(f"✅ Location found in database: {location_id}")
            
            # Get details
            query = text("""
                SELECT name, latitude, longitude 
                FROM shared.locations 
                WHERE location_id = :id
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {'id': location_id}).fetchone()
            
            return {
                'location_id': location_id,
                'name': result[0],
                'latitude': result[1],
                'longitude': result[2],
                'was_added': False,
                'satellite_passes': None,
                'weather_fetched': None
            }
        
        # Step 2: Location not found - ADD IT
        print(f"🆕 New location detected! Adding '{location_name}'...")
        print(f"⏳ This will take 30-60 seconds (geocoding + API calls)...\n")
        
        # Geocode
        geocoded = self.geocode(location_name)
        if not geocoded:
            raise ValueError(f"Could not find location: {location_name}")
        
        # Add to database
        location_id = self.add_to_database(geocoded)
        
        # Fetch satellite data
        satellite_count = self.fetch_satellite_passes(
            location_id,
            geocoded['latitude'],
            geocoded['longitude']
        )
        
        # Fetch weather
        weather_success = self.fetch_weather(
            location_id,
            geocoded['latitude'],
            geocoded['longitude']
        )
        
        print(f"\n{'='*70}")
        print(f"✅ {geocoded['short_name']} IS NOW AVAILABLE!")
        print(f"{'='*70}")
        print(f"Location ID: {location_id}")
        print(f"Coordinates: {geocoded['latitude']:.4f}°N, {geocoded['longitude']:.4f}°E")
        print(f"Satellite passes: {satellite_count}")
        print(f"Weather data: {'✅' if weather_success else '❌'}")
        print(f"{'='*70}\n")
        
        return {
            'location_id': location_id,
            'name': geocoded['short_name'],
            'latitude': geocoded['latitude'],
            'longitude': geocoded['longitude'],
            'was_added': True,
            'satellite_passes': satellite_count,
            'weather_fetched': weather_success
        }
    
    def get_all_locations(self) -> list:
        """
        Get list of all available locations
        
        Returns:
            List of dicts with location details
        """
        query = text("""
            SELECT 
                location_id,
                name,
                latitude,
                longitude,
                region,
                population,
                created_at
            FROM shared.locations
            ORDER BY 
                CASE 
                    WHEN population IS NOT NULL THEN 0 
                    ELSE 1 
                END,
                population DESC NULLS LAST,
                name
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [dict(row._mapping) for row in result]


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    manager = LocationManager()
    
    # Test 1: Check existing location
    print("\nTEST 1: Existing location (Mumbai)")
    result = manager.ensure_location_exists("Mumbai")
    print(f"Result: {result}\n")
    
    # Test 2: Add new location
    print("\nTEST 2: New location (Guwahati)")
    result = manager.ensure_location_exists("Guwahati")
    print(f"Result: {result}\n")
    
    # Test 3: List all locations
    print("\nTEST 3: All locations")
    locations = manager.get_all_locations()
    print(f"Total locations: {len(locations)}")
    for loc in locations[:10]:
        print(f"  - {loc['name']} ({loc['location_id']})")