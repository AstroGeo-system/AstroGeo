import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # External API keys
    NASA_API_KEY: str = "DEMO_KEY"
    COPERNICUS_CLIENT_ID: str = ""
    COPERNICUS_CLIENT_SECRET: str = ""
    N2YO_API_KEY: str = ""
    
    # API settings
    API_TITLE: str = "AstroGeo API"
    API_VERSION: str = "1.0.0"
    
    # External API URLs
    ISS_API_BASE: str = "http://api.open-notify.org"
    NASA_API_BASE: str = "https://api.nasa.gov"
    WEATHER_API_BASE: str = "https://api.open-meteo.com/v1"

    # Database settings
    # Using Supabase Transaction Pooler (IPv4, port 6543) — required for Render free tier
    # The direct db. hostname resolves to IPv6 which Render cannot reach.
    # Pooler user must include project ref: postgres.PROJECT_REF
    DB_HOST: str = "aws-1-ap-northeast-2.pooler.supabase.com"
    DB_PORT: str = "6543"
    DB_NAME: str = "postgres"
    DB_USER: str = "postgres.auyojdmjmgviztctbdsp"
    DB_PASSWORD: str = "*EPB8FSbV+Lr!2Z"
    DB_SCHEMA: str = "astronomy"

    @property
    def DATABASE_URL(self) -> str:
        import urllib.parse
        encoded_pw = urllib.parse.quote_plus(self.DB_PASSWORD)
        # sslmode=require is mandatory for Supabase; no_prepare=1 is needed for PgBouncer transaction pooler
        return f"postgresql://{self.DB_USER}:{encoded_pw}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?sslmode=require"
    
    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()