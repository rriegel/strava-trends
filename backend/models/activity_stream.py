from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.sql import func
from database import Base


class ActivityStream(Base):
    __tablename__ = "activity_streams"

    id = Column(BIGINT, primary_key=True, index=True)
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(BIGINT, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    stream_type = Column(String(50), nullable=False)  # heartrate, cadence, watts, latlng, altitude, velocity_smooth, grade_smooth

    # Stream data stored as JSONB array
    data = Column(JSONB, nullable=False)

    # Metadata
    series_type = Column(String(20), default="time")  # time or distance
    original_size = Column(BIGINT)
    resolution = Column(String(20))  # low, medium, high

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", "stream_type", name="uq_streams_user_activity_type"),
        Index("ix_activity_streams_user_id_activity_id", "user_id", "activity_id"),
    )
