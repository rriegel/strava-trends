from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import BIGINT, NUMERIC
from sqlalchemy.sql import func
from database import Base


class RouteCluster(Base):
    __tablename__ = "route_clusters"

    id = Column(BIGINT, primary_key=True, index=True)

    # Ownership: clusters are per-user, derived from per-user routes.
    user_id = Column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    centroid_route_id = Column(BIGINT, ForeignKey("routes.id", ondelete="SET NULL"), index=True)

    # Cluster metrics
    route_count = Column(BIGINT, default=0)
    avg_distance = Column(NUMERIC(10, 2))
    avg_elevation_gain = Column(NUMERIC(10, 2))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
