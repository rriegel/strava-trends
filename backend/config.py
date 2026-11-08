from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Application
    app_name: str = "Strava Trends API"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://postgres:***@localhost:5432/strava_trends"
    
    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/strava/callback"

    # Garmin Personal API (sync)
    garmin_api_key: str = ""
    garmin_api_key_expires_at: str = ""  # ISO date string; empty = unknown expiry
    garmin_fit_cache_dir: str = ""  # empty = <backend>/data/garmin_fit_cache
    
    # Authentication (JWT access + revocable refresh tokens)
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # short-lived; refresh tokens carry the session
    refresh_token_expire_days: int = 30
    
    # Feature flags
    dev_login_enabled: bool = False  # GET /auth/dev-login returns 403 unless True
    registration_enabled: bool = True  # POST /auth/register returns 403 unless True
    
    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Rate limiting
    rate_limit_per_minute: int = 100

settings = Settings()
