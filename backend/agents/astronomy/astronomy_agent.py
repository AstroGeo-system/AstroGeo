from sqlalchemy import create_engine
import os
from .modules.satellite_tracker import SatelliteTracker
from .modules.weather_analyzer import WeatherAnalyzer
from .modules.asteroid_monitor import AsteroidMonitor
from .modules.location_manager import LocationManager
from backend.config import settings

class AstronomyAgent:
    """
    Unified interface for astronomical queries
    Integrates satellite tracking, weather analysis, and asteroid monitoring
    """
    
    def __init__(self):
        """
        Initialize database connection and sub-modules
        """
        # Ensure we have a valid database URL
        db_url = settings.DATABASE_URL
        self.engine = create_engine(db_url)
        
        self.satellite_tracker = SatelliteTracker(self.engine)
        self.weather_analyzer = WeatherAnalyzer(self.engine)
        self.asteroid_monitor = AsteroidMonitor(self.engine)
        self.location_manager = LocationManager()
    
    def _ensure_location(self, location_name):
        """
        Ensure location exists and return feedback message if added
        """
        info = self.location_manager.ensure_location_exists(location_name)
        
        if info['was_added']:
            return f"""
🌟 **New Location Added: {info['name']}**
📍 Coordinates: {info['latitude']:.4f}°N, {info['longitude']:.4f}°E
📡 Found {info['satellite_passes']} satellite passes
☁️ Weather data initialized
"""
        return None

    # -------------------------------------------------------------------------
    # Satellite Tracking Methods
    # -------------------------------------------------------------------------
    def get_satellite_passes(self, location, satellite_id=None, hours_ahead=24):
        """Delegate to SatelliteTracker"""
        # Ensure location exists first
        self._ensure_location(location)
        return self.satellite_tracker.get_passes(location, satellite_id, hours_ahead)
    
    def get_next_iss_pass(self, location):
        """Delegate to SatelliteTracker"""
        # Check location and get welcome message
        welcome_msg = self._ensure_location(location)
        
        result = self.satellite_tracker.get_next_iss_pass(location)
        
        # Inject message if strictly returning a dict
        if result and welcome_msg:
            result['user_message'] = welcome_msg
        elif welcome_msg and result is None:
             # If no pass found but we have a welcome message, return it with a status
             return {
                 "user_message": welcome_msg,
                 "status": "No upcoming ISS passes found in the next 48 hours."
             }
            
        return result
    
    def find_best_viewing_location(self, satellite_id='ISS', time_window='tonight'):
        """Delegate to SatelliteTracker"""
        return self.satellite_tracker.find_best_viewing_location(satellite_id, time_window)
    
    def get_satellite_position(self, satellite_id='ISS'):
        """Delegate to SatelliteTracker or ISSService"""
        if satellite_id == 'ISS':
            try:
                from backend.services.external.iss_service import iss_service
                import asyncio
                pos = asyncio.run(iss_service.get_current_position())
                return {
                    "latitude": pos["latitude"],
                    "longitude": pos["longitude"],
                    "altitude_km": 408.0,
                    "velocity_km_s": 7.66,
                    "is_in_sunlight": True,
                    "position_time": pos["timestamp"]
                }
            except Exception:
                pass
        return self.satellite_tracker.get_satellite_position(satellite_id)
    
    # -------------------------------------------------------------------------
    # Weather Analysis Methods
    # -------------------------------------------------------------------------
    def get_observation_conditions(self, location):
        """Delegate to WeatherAnalyzer"""
        self._ensure_location(location)
        return self.weather_analyzer.get_current_conditions(location)
    
    def get_best_viewing_window(self, location, hours_ahead=24, min_quality=70):
        """Delegate to WeatherAnalyzer"""
        self._ensure_location(location)
        return self.weather_analyzer.find_best_windows(location, hours_ahead, min_quality)
    
    def compare_forecast_vs_current(self, location):
        """Delegate to WeatherAnalyzer"""
        self._ensure_location(location)
        return self.weather_analyzer.compare_forecast_vs_current(location)
    
    # -------------------------------------------------------------------------
    # Asteroid Monitoring Methods
    # -------------------------------------------------------------------------
    def get_asteroid_profile(self, asteroid_id):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.get_profile(asteroid_id)
    
    def get_upcoming_asteroid_approaches(self, days_ahead=30, min_distance=None, risk_level=None):
        """Delegate to AsteroidMonitor"""
        import asyncio
        try:
            return asyncio.run(self.asteroid_monitor.get_upcoming_approaches_async(days_ahead, min_distance, risk_level))
        except RuntimeError:
            return self.asteroid_monitor.get_next_approaches_from_db(limit=20)
    
    def get_asteroids_by_cluster(self, cluster_id, limit=10):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.get_cluster_members(cluster_id, limit)
    
    def get_high_risk_asteroids(self, min_risk_score=60):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.get_high_risk_asteroids(min_risk_score)
    
    def search_asteroids(self, search_term):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.search_asteroids(search_term)
    
    def get_asteroid_temporal_pattern(self, asteroid_id):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.get_temporal_pattern(asteroid_id)
    
    def compare_asteroids(self, asteroid_id_1, asteroid_id_2):
        """Delegate to AsteroidMonitor"""
        return self.asteroid_monitor.compare_asteroids(asteroid_id_1, asteroid_id_2)
    
    # -------------------------------------------------------------------------
    # Integrated Methods
    # -------------------------------------------------------------------------
    def can_i_observe_tonight(self, location, object_type='satellite'):
        """
        Cross-module integration: Checks weather and satellite passes
        """
        # Ensure location exists
        welcome_msg = self._ensure_location(location)
        
        # 1. Check weather first
        conditions = self.get_observation_conditions(location)
        if not conditions:
            return {"can_observe": False, "reason": "Location not found or no weather data"}
            
        weather_suitable = conditions.get('suitable_for_astronomy', False)
        weather_desc = conditions.get('weather_description', 'unknown')
        cloud_cover = conditions.get('cloud_cover_percent', 100)
        
        result = {}
        
        if not weather_suitable:
            result = {
                "can_observe": False, 
                "reason": f"Poor weather conditions: {weather_desc} ({cloud_cover}% clouds).",
                "weather_details": conditions
            }
        
        # 2. Check objects
        elif object_type == 'satellite':
            passes = self.get_satellite_passes(location, hours_ahead=12)
            visible_passes = [p for p in passes if p.get('combined_score', 0) > 50]
            
            if not visible_passes:
                result = {
                    "can_observe": False,
                    "reason": "Good weather, but no high-quality satellite passes visible tonight."
                }
            else:    
                best_pass = visible_passes[0]
                result = {
                    "can_observe": True,
                    "reason": f"Yes! Weather is {weather_desc}. Best pass: {best_pass['name']} at {best_pass['rise_time']}.",
                    "details": best_pass
                }
        else:
            result = {"can_observe": True, "reason": "Weather looks good for observation."}
            
        # Inject welcome message
        if welcome_msg:
            result['user_message'] = welcome_msg
            
        return result

    def get_observation_plan(self, location, date=None):
        """
        Generates a comprehensive plan
        """
        welcome_msg = self._ensure_location(location)
        
        conditions = self.get_observation_conditions(location)
        windows = self.get_best_viewing_window(location)
        passes = self.get_satellite_passes(location)
        
        # Pull real asteroid risk metrics from PostgreSQL ML predictions
        risk_metrics = {'level': 'Low', 'high_risk_count': 0, 'top_asteroid': None}
        try:
            high_risk = self.asteroid_monitor.get_high_risk_asteroids(min_risk_score=50)
            if high_risk:
                top = high_risk[0]
                score = top.get('improved_risk_score', 0)
                risk_metrics = {
                    'level': 'High' if score >= 75 else 'Moderate' if score >= 50 else 'Low',
                    'high_risk_count': len(high_risk),
                    'top_asteroid': top.get('asteroid_id'),
                    'top_score': round(score, 2),
                    'top_category': top.get('adaptive_risk_category', 'Unknown'),
                }
        except Exception:
            pass  # Graceful fallback — keep default Low

        plan = {
            'location': location,
            'current_weather': conditions,
            'best_viewing_windows': windows,
            'satellite_passes': passes[:5],  # Top 5
            'risk_metrics': risk_metrics,
        }
        
        if welcome_msg:
            plan['user_message'] = welcome_msg
            
        return plan
    
    def whats_happening_tonight(self, location):
        """
        Summary of tonight's events
        """
        return self.get_observation_plan(location)
    
    # -------------------------------------------------------------------------
    # Location Management
    # -------------------------------------------------------------------------
    def add_location(self, location_name=None, latitude=None, longitude=None):
        """Delegate to LocationManager"""
        return self.location_manager.add_to_database({
            'short_name': location_name,
            'latitude': latitude,
            'longitude': longitude,
            'country': 'Unknown',
            'region': 'Unknown'
        })
    
    def get_available_locations(self):
        """Delegate to LocationManager"""
        return self.location_manager.get_all_locations()