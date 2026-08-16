from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class ComputedMetric(Base):
    __tablename__ = "computed_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # hr_pace_ratio, grade_adjusted_pace, running_economy, heart_rate_drift
    
    # Metric value
    value = Column(Float, nullable=False)
    
    # Metadata
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
