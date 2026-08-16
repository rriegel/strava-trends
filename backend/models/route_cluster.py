from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class RouteCluster(Base):
    __tablename__ = "route_clusters"

    id = Column(Integer, primary_key=True, index=True)
    centroid_route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), index=True)
    
    # Cluster metrics
    route_count = Column(Integer, default=0)
    avg_distance = Column(Float)
    avg_elevation_gain = Column(Float)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
