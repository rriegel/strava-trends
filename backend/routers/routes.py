from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.route import Route
from models.route_cluster import RouteCluster
from models.activity import Activity

router = APIRouter()

@router.get("")
async def list_routes(
    sort_by: str = Query("activity_count", description="Sort: activity_count, distance, elevation_gain"),
    sort_order: str = Query("desc"),
    min_activity_count: Optional[int] = None,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List routes with filtering and sorting"""
    query = db.query(Route)
    
    if min_activity_count:
        query = query.filter(Route.activity_count >= min_activity_count)
    
    # TODO: Implement spatial filtering with bounding box or radius
    
    sort_column = getattr(Route, sort_by, Route.activity_count)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    total = query.count()
    routes = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "routes": [
            {
                "id": r.id,
                "name": r.name,
                "distance": r.distance,
                "elevation_gain": r.elevation_gain,
                "activity_count": r.activity_count,
                "cluster_id": r.cluster_id,
                "start_lat": r.start_lat,
                "start_lng": r.start_lng,
                "polyline": r.polyline
            }
            for r in routes
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }

@router.get("/{route_id}")
async def get_route(route_id: int, db: Session = Depends(get_db)):
    """Get route details with activities"""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    activities = db.query(Activity).filter(Activity.route_id == route_id).all()
    
    return {
        "id": route.id,
        "name": route.name,
        "distance": route.distance,
        "elevation_gain": route.elevation_gain,
        "activity_count": route.activity_count,
        "cluster_id": route.cluster_id,
        "start_lat": route.start_lat,
        "start_lng": route.start_lng,
        "end_lat": route.end_lat,
        "end_lng": route.end_lng,
        "polyline": route.polyline,
        "activities": [
            {
                "id": a.id,
                "start_date": a.start_date.isoformat(),
                "moving_time": a.moving_time,
                "average_speed": a.average_speed,
                "average_heartrate": a.average_heartrate,
                "distance_bucket": a.distance_bucket,
                "effort_zone": a.effort_zone
            }
            for a in activities
        ],
        "trends": {
            "average_speed": {"slope": 0, "direction": "stable"},
            "average_heartrate": {"slope": 0, "direction": "stable"}
        }
    }

class RouteRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.patch("/{route_id}")
async def rename_route(
    route_id: int,
    payload: RouteRenameRequest,
    db: Session = Depends(get_db),
):
    """Rename a route (user-facing label; does not affect matching)"""
    # Validate AFTER stripping so whitespace-only names can't sneak through
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Route name cannot be empty")

    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.name = name
    db.commit()
    db.refresh(route)

    return {
        "id": route.id,
        "name": route.name,
        "distance": route.distance,
        "elevation_gain": route.elevation_gain,
        "activity_count": route.activity_count,
        "cluster_id": route.cluster_id,
        "start_lat": route.start_lat,
        "start_lng": route.start_lng,
        "polyline": route.polyline,
    }


@router.get("/clusters/{cluster_id}")
async def get_route_cluster(cluster_id: int, db: Session = Depends(get_db)):
    """Get route cluster details"""
    cluster = db.query(RouteCluster).filter(RouteCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    routes = db.query(Route).filter(Route.cluster_id == cluster_id).all()
    
    return {
        "id": cluster.id,
        "centroid_route_id": cluster.centroid_route_id,
        "route_count": cluster.route_count,
        "avg_distance": cluster.avg_distance,
        "avg_elevation_gain": cluster.avg_elevation_gain,
        "routes": [
            {
                "id": r.id,
                "name": r.name,
                "distance": r.distance,
                "elevation_gain": r.elevation_gain,
                "activity_count": r.activity_count
            }
            for r in routes
        ]
    }
