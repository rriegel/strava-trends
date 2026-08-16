from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import BIGINT, NUMERIC
from sqlalchemy.sql import func
from database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(BIGINT, primary_key=True, index=True)
    name = Column(String(255))

    # GPS data
    polyline = Column(Text)  # encoded polyline
    polyline_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Metrics
    distance = Column(NUMERIC(10, 2))  # meters
    elevation_gain = Column(NUMERIC(10, 2))  # meters

    # Start/end coordinates
    start_lat = Column(NUMERIC(9, 6))
    start_lng = Column(NUMERIC(9, 6))
    end_lat = Column(NUMERIC(9, 6))
    end_lng = Column(NUMERIC(9, 6))

    # Clustering
    cluster_id = Column(BIGINT, ForeignKey("route_clusters.id", ondelete="SET NULL"), index=True)

    # Activity count (denormalized)
    activity_count = Column(BIGINT, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
