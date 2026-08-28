from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BIGINT, primary_key=True, index=True)
    strava_athlete_id = Column(BIGINT, unique=True, nullable=True, index=True)

    # Profile
    username = Column(String(100), unique=True, nullable=True)
    firstname = Column(String(100))
    lastname = Column(String(100))
    email = Column(String(255), unique=True, nullable=True)
    profile_url = Column(String(500))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))

    # OAuth tokens (encrypted in production) - nullable for non-Strava users
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Sync state
    last_sync_at = Column(DateTime)
    last_synced_activity_id = Column(BIGINT)
    sync_status = Column(String(20), default="idle")  # idle, syncing, error

    # Preferences
    default_distance_unit = Column(String(10), default="metric")  # metric, imperial
    preferred_hr_zones = Column(JSONB)  # {"zone_1": {"min": 0, "max": 115}, ...}
    max_hr = Column(Integer)  # User-configured max HR override (bpm)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
