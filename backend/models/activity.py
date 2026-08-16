from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import BIGINT, NUMERIC
from sqlalchemy.sql import func
from database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(BIGINT, primary_key=True, index=True)
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strava_id = Column(BIGINT, nullable=False)

    # Basic info
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # Run, Ride, Swim, etc.
    sport_type = Column(String(50))  # TrailRun, VirtualRide, etc.

    # Timing
    start_date = Column(DateTime(timezone=True), nullable=False)
    start_date_local = Column(DateTime(timezone=True), nullable=False)
    moving_time = Column(BIGINT)  # seconds
    elapsed_time = Column(BIGINT)  # seconds

    # Distance & elevation
    distance = Column(NUMERIC(10, 2))  # meters
    total_elevation_gain = Column(NUMERIC(10, 2))  # meters
    average_speed = Column(NUMERIC(6, 3))  # m/s
    max_speed = Column(NUMERIC(6, 3))  # m/s

    # Heart rate
    average_heartrate = Column(NUMERIC(5, 1))  # bpm
    max_heartrate = Column(NUMERIC(5, 1))  # bpm
    has_heartrate = Column(Boolean, default=False)

    # Power
    average_watts = Column(NUMERIC(7, 1))
    weighted_average_watts = Column(NUMERIC(7, 1))
    max_watts = Column(NUMERIC(7, 1))
    kilojoules = Column(NUMERIC(10, 2))

    # Cadence
    average_cadence = Column(NUMERIC(5, 1))  # spm

    # Suffer score
    suffer_score = Column(NUMERIC(5, 1))

    # Device & gear
    device_name = Column(String(255))
    gear_id = Column(String(50))

    # Classifications (denormalized for performance)
    distance_bucket = Column(String(20))  # 5K, 10K, Half, Marathon, Other
    effort_zone = Column(String(20))  # easy, moderate, hard, very_hard
    terrain_type = Column(String(20))  # flat, rolling, hilly, trail

    # Route matching
    route_id = Column(BIGINT, ForeignKey("routes.id", ondelete="SET NULL"), index=True)

    # Stream availability
    has_streams = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "strava_id", name="uq_activities_user_strava"),
        Index("ix_activities_user_id_type_start_date", "user_id", "type", "start_date"),
        Index("ix_activities_user_id_start_date_local", "user_id", "start_date_local"),
        Index("ix_activities_user_id_distance_bucket", "user_id", "distance_bucket"),
        Index("ix_activities_user_id_effort_zone", "user_id", "effort_zone"),
        Index("ix_activities_user_id_route_id", "user_id", "route_id"),
    )
