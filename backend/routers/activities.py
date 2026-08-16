from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from database import get_db
from models.activity import Activity
from models.activity_stream import ActivityStream

router = APIRouter()

@router.get("/")
async def list_activities(
    type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    distance_bucket: Optional[str] = None,
    effort_zone: Optional[str] = None,
    terrain_type: Optional[str] = None,
    route_id: Optional[int] = None,
    sort_by: str = "start_date",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List activities with filtering and pagination"""
    query = db.query(Activity)
    
    # Apply filters
    if type:
        query = query.filter(Activity.type == type)
    if start_date:
        query = query.filter(Activity.start_date >= start_date)
    if end_date:
        query = query.filter(Activity.start_date <= end_date)
    if distance_bucket:
        query = query.filter(Activity.distance_bucket == distance_bucket)
    if effort_zone:
        query = query.filter(Activity.effort_zone == effort_zone)
    if terrain_type:
        query = query.filter(Activity.terrain_type == terrain_type)
    if route_id:
        query = query.filter(Activity.route_id == route_id)
    
    # Apply sorting
    sort_column = getattr(Activity, sort_by, Activity.start_date)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Pagination
    total = query.count()
    activities = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "activities": [
            {
                "id": a.id,
                "strava_id": a.strava_id,
                "name": a.name,
                "type": a.type,
                "sport_type": a.sport_type,
                "start_date": a.start_date.isoformat(),
                "moving_time": a.moving_time,
                "distance": a.distance,
                "total_elevation_gain": a.total_elevation_gain,
                "average_speed": a.average_speed,
                "average_heartrate": a.average_heartrate,
                "max_heartrate": a.max_heartrate,
                "average_cadence": a.average_cadence,
                "average_watts": a.average_watts,
                "suffer_score": a.suffer_score,
                "device_name": a.device_name,
                "distance_bucket": a.distance_bucket,
                "effort_zone": a.effort_zone,
                "terrain_type": a.terrain_type,
                "route_id": a.route_id,
                "has_streams": a.has_streams
            }
            for a in activities
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }

@router.get("/{activity_id}")
async def get_activity(activity_id: int, db: Session = Depends(get_db)):
    """Get activity details"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return {
        "id": activity.id,
        "strava_id": activity.strava_id,
        "name": activity.name,
        "type": activity.type,
        "sport_type": activity.sport_type,
        "start_date": activity.start_date.isoformat(),
        "moving_time": activity.moving_time,
        "elapsed_time": activity.elapsed_time,
        "distance": activity.distance,
        "total_elevation_gain": activity.total_elevation_gain,
        "average_speed": activity.average_speed,
        "max_speed": activity.max_speed,
        "average_heartrate": activity.average_heartrate,
        "max_heartrate": activity.max_heartrate,
        "has_heartrate": activity.has_heartrate,
        "average_watts": activity.average_watts,
        "weighted_average_watts": activity.weighted_average_watts,
        "max_watts": activity.max_watts,
        "average_cadence": activity.average_cadence,
        "suffer_score": activity.suffer_score,
        "kilojoules": activity.kilojoules,
        "device_name": activity.device_name,
        "gear_id": activity.gear_id,
        "distance_bucket": activity.distance_bucket,
        "effort_zone": activity.effort_zone,
        "terrain_type": activity.terrain_type,
        "route_id": activity.route_id,
        "created_at": activity.created_at.isoformat(),
        "updated_at": activity.updated_at.isoformat()
    }

@router.get("/{activity_id}/streams")
async def get_activity_streams(
    activity_id: int,
    stream_types: Optional[str] = None,
    resolution: str = "medium",
    db: Session = Depends(get_db)
):
    """Get activity streams (time-series data)"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    query = db.query(ActivityStream).filter(ActivityStream.activity_id == activity_id)
    
    if stream_types:
        types = stream_types.split(",")
        query = query.filter(ActivityStream.stream_type.in_(types))
    
    streams = query.all()
    
    return {
        "activity_id": activity_id,
        "streams": {
            s.stream_type: {
                "data": s.data,
                "series_type": s.series_type,
                "original_size": s.original_size,
                "resolution": s.resolution
            }
            for s in streams
        }
    }
