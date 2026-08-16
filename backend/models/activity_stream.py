from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base

class ActivityStream(Base):
    __tablename__ = "activity_streams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    stream_type = Column(String(50), nullable=False)  # heartrate, cadence, watts, latlng, altitude, velocity_smooth, grade_smooth
    
    # Stream data stored as JSON array
    data = Column(JSON, nullable=False)
    
    # Metadata
    series_type = Column(String(20), default="time")  # time or distance
    original_size = Column(Integer)
    resolution = Column(String(20))  # low, medium, high
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
