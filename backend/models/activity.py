from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strava_id = Column(Integer, nullable=False, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # Run, Ride, Swim, etc.
    sport_type = Column(String(50))  # TrailRun, VirtualRide, etc.
    
    # Timing
    start_date = Column(DateTime(timezone=True), nullable=False)
    start_date_local = Column(DateTime(timezone=True), nullable=False)
    moving_time = Column(Integer)  # seconds
    elapsed_time = Column(Integer)  # seconds
    
    # Distance & elevation
    distance = Column(Float)  # meters
    total_elevation_gain = Column(Float)  # meters
    average_speed = Column(Float)  # m/s
    max_speed = Column(Float)  # m/s
    
    # Heart rate
    average_heartrate = Column(Float)  # bpm
    max_heartrate = Column(Float)  # bpm
    has_heartrate = Column(Boolean, default=False)
    
    # Power
    average_watts = Column(Float)
    weighted_average_watts = Column(Float)
    max_watts = Column(Float)
    kilojoules = Column(Float)
    
    # Cadence
    average_cadence = Column(Float)  # spm
    
    # Suffer score
    suffer_score = Column(Float)
    
    # Device & gear
    device_name = Column(String(255))
    gear_id = Column(String(50))
    
    # Classifications (denormalized for performance)
    distance_bucket = Column(String(20))  # 5K, 10K, Half, Marathon, Other
    effort_zone = Column(String(20))  # easy, moderate, hard, very_hard
    terrain_type = Column(String(20))  # flat, rolling, hilly, trail
    
    # Route matching
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), index=True)
    
    # Stream availability
    has_streams = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
