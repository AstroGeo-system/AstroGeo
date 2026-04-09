import httpx
from typing import Dict, List
from backend.config import settings

class WeatherService:
    """Handles weather data from Open-Meteo"""
    
    def __init__(self):
        self.base_url = settings.WEATHER_API_BASE
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float
    ) -> Dict:
        """
        Get current weather conditions
        
        Returns:
            {
                "timestamp": "2025-01-27T10:30:00Z",
                "temperature_c": 22.5,
                "cloud_cover_percent": 15,
                "humidity_percent": 65,
                "wind_speed_kmh": 12.3
            }
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,cloud_cover,relative_humidity_2m,wind_speed_10m"
            }
            
            response = await self.client.get(
                f"{self.base_url}/forecast",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            current = data["current"]
            return {
                "timestamp": current["time"],
                "temperature_c": current["temperature_2m"],
                "cloud_cover_percent": current["cloud_cover"],
                "humidity_percent": current["relative_humidity_2m"],
                "wind_speed_kmh": current["wind_speed_10m"]
            }
        
        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch weather: {str(e)}")
    
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7
    ) -> List[Dict]:
        """
        Get weather forecast
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (max 16)
        
        Returns:
            List of daily forecasts
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,temperature_2m_min,cloud_cover_mean",
                "forecast_days": min(days, 16)  # API max is 16
            }
            
            response = await self.client.get(
                f"{self.base_url}/forecast",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            daily = data["daily"]
            forecasts = []
            for i in range(len(daily["time"])):
                forecasts.append({
                    "date": daily["time"][i],
                    "temp_max_c": daily["temperature_2m_max"][i],
                    "temp_min_c": daily["temperature_2m_min"][i],
                    "cloud_cover_percent": daily["cloud_cover_mean"][i]
                })
            
            return forecasts
        
        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch forecast: {str(e)}")
    
    async def close(self):
        await self.client.aclose()

# Create singleton
weather_service = WeatherService()