from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.route import Route
from models.route_cluster import RouteCluster
from models.activity import Activity
from models.activity_stream import ActivityStream
from models.user import User
from routers.auth import get_current_user
from services.route_comparison import (
    compute_race_curve,
    compute_splits,
    decimate_track,
    is_direction_reversed,
)

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List routes with filtering and sorting (per-user)."""
    query = db.query(Route).filter(Route.user_id == current_user.id)

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
async def get_route(
    route_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get route details with activities"""
    route = db.query(Route).filter(
        Route.id == route_id,
        Route.user_id == current_user.id,
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    activities = db.query(Activity).filter(
        Activity.route_id == route_id,
        Activity.user_id == current_user.id,
    ).all()

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
                "distance": float(a.distance) if a.distance is not None else None,
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

MIN_COMPARE_TRACKS = 2
MAX_COMPARE_TRACKS = 5


def _activity_compare_payload(
    activity: Activity, streams: dict, route: Route, checkpoint_interval_m: float
) -> dict:
    """Build one activity's compare payload from its (time, distance) streams."""
    time_stream = streams.get("time")
    distance_stream = streams.get("distance")

    summary = {
        "id": activity.id,
        "name": activity.name,
        "start_date": activity.start_date.isoformat(),
        "moving_time": activity.moving_time,
        "elapsed_time": activity.elapsed_time,
        "distance": float(activity.distance) if activity.distance is not None else None,
        "average_speed": float(activity.average_speed) if activity.average_speed is not None else None,
        "average_heartrate": float(activity.average_heartrate) if activity.average_heartrate is not None else None,
        "total_elevation_gain": float(activity.total_elevation_gain) if activity.total_elevation_gain is not None else None,
    }

    latlng = streams.get("latlng") or []
    payload = {
        "id": activity.id,
        "summary": summary,
        "track": decimate_track(latlng) if latlng else [],
        "race_plot": None,
        "splits": None,
        "direction_reversed": False,
    }

    if not time_stream or not distance_stream or len(time_stream) != len(distance_stream):
        return payload

    # Reverse-run detection uses the raw track; splits/plot use the streams
    if route.start_lat is not None and route.end_lat is not None and len(latlng) >= 2:
        payload["direction_reversed"] = is_direction_reversed(
            latlng,
            (route.start_lat, route.start_lng),
            (route.end_lat, route.end_lng),
        )
    if payload["direction_reversed"]:
        return payload

    curve = compute_race_curve(distance_stream, time_stream)
    if curve:
        payload["race_plot"] = {"distances": curve[0], "elapsed_seconds": curve[1]}
        payload["splits"] = compute_splits(
            distance_stream, time_stream, checkpoint_interval_m
        )
    return payload


@router.get("/{route_id}/compare")
async def compare_route_activities(
    route_id: int,
    activity_ids: str = Query(..., description="Comma-separated activity IDs (2-5)"),
    checkpoint_interval_m: float = Query(
        1000.0,
        gt=0.0,
        le=5000.0,
        description="Split segment length in meters (1000 = 1 km, 800, 400, ...)",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare 2-5 activities on one route: GPS overlay, race plot, splits.

    Race plot + splits require persisted `time` + `distance` streams
    (present on activities uploaded after the route-comparison feature).
    Activities without them (or run in reverse) still contribute their
    GPS track and summary.
    """
    route = db.query(Route).filter(
        Route.id == route_id,
        Route.user_id == current_user.id,
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    try:
        ids = [int(x) for x in activity_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="activity_ids must be comma-separated integers")

    ids = list(dict.fromkeys(ids))  # dedupe, preserve order
    if not (MIN_COMPARE_TRACKS <= len(ids) <= MAX_COMPARE_TRACKS):
        raise HTTPException(
            status_code=422,
            detail=f"activity_ids must contain {MIN_COMPARE_TRACKS}-{MAX_COMPARE_TRACKS} unique IDs",
        )

    activities = (
        db.query(Activity)
        .filter(
            Activity.id.in_(ids),
            Activity.route_id == route_id,
            Activity.user_id == current_user.id,
        )
        .all()
    )
    found_ids = {a.id for a in activities}
    missing = [i for i in ids if i not in found_ids]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Activities not found on route {route_id}: {missing}",
        )
    activities.sort(key=lambda a: ids.index(a.id))  # keep requested order

    stream_types = ("time", "distance", "latlng")
    streams_by_activity: dict = {}
    rows = (
        db.query(ActivityStream.activity_id, ActivityStream.stream_type, ActivityStream.data)
        .filter(
            ActivityStream.activity_id.in_(ids),
            ActivityStream.stream_type.in_(stream_types),
        )
        .all()
    )
    for activity_id, stream_type, data in rows:
        streams_by_activity.setdefault(activity_id, {})[stream_type] = data

    return {
        "route": {
            "id": route.id,
            "name": route.name,
            "distance": route.distance,
            "elevation_gain": route.elevation_gain,
            "activity_count": route.activity_count,
        },
        "activities": [
            _activity_compare_payload(
                a, streams_by_activity.get(a.id, {}), route, checkpoint_interval_m
            )
            for a in activities
        ],
    }


class RouteRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.patch("/{route_id}")
async def rename_route(
    route_id: int,
    payload: RouteRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a route (user-facing label; does not affect matching)"""
    # Validate AFTER stripping so whitespace-only names can't sneak through
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Route name cannot be empty")

    route = db.query(Route).filter(
        Route.id == route_id,
        Route.user_id == current_user.id,
    ).first()
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
async def get_route_cluster(
    cluster_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get route cluster details (per-user)."""
    cluster = db.query(RouteCluster).filter(
        RouteCluster.id == cluster_id,
        RouteCluster.user_id == current_user.id,
    ).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    routes = db.query(Route).filter(
        Route.cluster_id == cluster_id,
        Route.user_id == current_user.id,
    ).all()

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
