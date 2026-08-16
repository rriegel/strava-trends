from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str = "Strava Trends API"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://user:password@localhost/strava_trends"
    
    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/strava/callback"
    
    # Authentication
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()
