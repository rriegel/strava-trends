from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import BIGINT, NUMERIC
from sqlalchemy.sql import func
from database import Base


class ComputedMetric(Base):
    __tablename__ = "computed_metrics"

    id = Column(BIGINT, primary_key=True, index=True)
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(BIGINT, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    metric_type = Column(String(50), nullable=False)  # hr_pace_ratio, grade_adjusted_pace, running_economy, heart_rate_drift

    # Metric value
    value = Column(NUMERIC(10, 4), nullable=False)

    # Metadata
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", "metric_type", name="uq_metrics_user_activity_type"),
        Index("ix_computed_metrics_user_id_metric_type", "user_id", "metric_type"),
    )
