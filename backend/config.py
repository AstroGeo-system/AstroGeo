import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # External API keys
    NASA_API_KEY: str
    COPERNICUS_CLIENT_ID: str
    NASA_API_KEY: str
    COPERNICUS_CLIENT_ID: str
    COPERNICUS_CLIENT_SECRET: str
    N2YO_API_KEY: str
    
    # API settings
    API_TITLE: str = "AstroGeo API"
    API_VERSION: str = "1.0.0"
    
    # External API URLs
    ISS_API_BASE: str = "http://api.open-notify.org"
    NASA_API_BASE: str = "https://api.nasa.gov"
    WEATHER_API_BASE: str = "https://api.open-meteo.com/v1"

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "astrogeo_db"
    DB_USER: str = "khushikhanna"
    DB_PASSWORD: str
    DB_SCHEMA: str = "public"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()