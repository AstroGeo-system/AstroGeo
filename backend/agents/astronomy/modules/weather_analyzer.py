from sqlalchemy import text
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class WeatherAnalyzer:
    """
    Handles all weather-related queries and analysis
    """
    
    def __init__(self, engine):
        self.engine = engine
    
    def get_current_conditions(self, location: str) -> Optional[Dict[str, Any]]:
        """
        Query weather.current_observation_conditions
        """
        query = text("""
            SELECT 
                location_name,
                observed_at,
                temperature_celsius,
                cloud_cover_percent,
                visibility_km,
                wind_speed_kmh,
                weather_description,
                overall_quality_score,
                quality_category,
                suitable_for_astronomy,
                quality_description,
                sunset_time,
                sunrise_time,
                is_currently_night
            FROM weather.current_observation_conditions
            WHERE location_name ILIKE :location
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'location': f"%{location}%"}).fetchone()
            if result:
                return dict(result._mapping)
            return None
    
    def find_best_windows(self, location: str, hours_ahead: int = 24, min_quality: int = 70) -> List[Dict[str, Any]]:
        """
        Query weather.hourly_forecast and find windows with good quality
        Note: The schema has `weather.hourly_forecast` but quality scores are in `weather.observation_quality`
        We need to join them or query `observation_quality` directly if it has forecast data.
        The schema says `observation_quality` has `is_forecast` column.
        """
        query = text("""
            SELECT 
                datetime as start_time,
                overall_quality_score,
                cloud_cover_percent,
                quality_description
            FROM weather.observation_quality oq
            JOIN shared.locations l ON oq.location_id = l.location_id
            WHERE l.name ILIKE :location
              AND oq.datetime BETWEEN NOW() AND NOW() + INTERVAL ':hours hours'
              AND oq.overall_quality_score >= :min_score
            ORDER BY oq.datetime ASC
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'location': f"%{location}%",
                'hours': hours_ahead,
                'min_score': min_quality
            })
            
            # Simple aggregation of consecutive hours could be done here
            # For now returning raw hours
            windows = []
            for row in result:
                windows.append(dict(row._mapping))
            
            return windows

    def compare_forecast_vs_current(self, location: str) -> Dict[str, Any]:
        """
        Compare current conditions vs next 6 hours
        """
        current = self.get_current_conditions(location)
        if not current:
            return {"error": "No current data"}
            
        forecasts = self.find_best_windows(location, hours_ahead=6, min_quality=0)
        
        # Calculate trend
        curr_score = current.get('overall_quality_score', 0)
        if not forecasts:
             return {"trend": "Unknown", "details": "No forecast data"}
             
        avg_future_score = sum(f['overall_quality_score'] for f in forecasts) / len(forecasts)
        
        trend = "Stable"
        if avg_future_score > curr_score + 10:
            trend = "Improving"
        elif avg_future_score < curr_score - 10:
            trend = "Worsening"
            
        return {
            "current_score": curr_score,
            "future_avg_score": avg_future_score,
            "trend": trend,
            "recommendation": "Wait for better conditions" if trend == "Improving" else "Observe now"
        }
