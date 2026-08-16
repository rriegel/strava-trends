from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class EffortGroup(Base):
    __tablename__ = "effort_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Grouping info
    group_type = Column(String(30), nullable=False)  # hr_zone, power_zone, perceived_effort
    group_label = Column(String(50), nullable=False)  # Zone 1, Zone 2, Easy, Moderate, etc.
    group_value = Column(Integer)  # Numeric zone (1, 2, 3, etc.)
    
    # Time in zone
    time_in_zone = Column(Integer)  # seconds spent in this zone
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
