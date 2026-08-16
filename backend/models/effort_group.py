from sqlalchemy import Column, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.sql import func
from database import Base


class EffortGroup(Base):
    __tablename__ = "effort_groups"

    id = Column(BIGINT, primary_key=True, index=True)
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(BIGINT, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)

    # Grouping info
    group_type = Column(String(30), nullable=False)  # hr_zone, power_zone, perceived_effort
    group_label = Column(String(50), nullable=False)  # Zone 1, Zone 2, Easy, Moderate, etc.
    group_value = Column(BIGINT)  # Numeric zone (1, 2, 3, etc.)

    # Time in zone
    time_in_zone = Column(BIGINT)  # seconds spent in this zone

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", "group_type", "group_label", name="uq_effort_groups_user_activity_group"),
        Index("ix_effort_groups_user_id_group_type", "user_id", "group_type"),
    )
