from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    
    # GPS data
    polyline = Column(Text)  # encoded polyline
    polyline_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Metrics
    distance = Column(Float)  # meters
    elevation_gain = Column(Float)  # meters
    
    # Start/end coordinates
    start_lat = Column(Float)
    start_lng = Column(Float)
    end_lat = Column(Float)
    end_lng = Column(Float)
    
    # Clustering
    cluster_id = Column(Integer, ForeignKey("route_clusters.id", ondelete="SET NULL"), index=True)
    
    # Activity count (denormalized)
    activity_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
