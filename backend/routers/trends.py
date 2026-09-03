from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from services.trends_service import TrendsService

router = APIRouter()


@router.get("/metrics")
async def get_metric_trend(
    metric_type: str = Query(..., description="Metric to trend (hr_pace_ratio, average_speed, etc.)"),
    activity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    distance_bucket: Optional[str] = None,
    route_id: Optional[int] = None,
    aggregation: Optional[str] = Query(None, description="daily, weekly, monthly"),
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db)
):
    """Get time-series trend data for a specific metric"""
    service = TrendsService(db)

    return service.get_metric_trend(
        user_id=user_id,
        metric_type=metric_type,
        activity_type=activity_type,
        distance_bucket=distance_bucket,
        start_date=start_date,
        end_date=end_date,
        aggregation=aggregation,
        route_id=route_id
    )


@router.get("/metrics/multi")
async def get_multi_metric_trend(
    metric_types: str = Query(..., description="Comma-separated metrics"),
    activity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    distance_bucket: Optional[str] = None,
    route_id: Optional[int] = None,
    aggregation: Optional[str] = None,
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db)
):
    """Get trend data for multiple metrics simultaneously"""
    service = TrendsService(db)

    metric_types_list = [m.strip() for m in metric_types.split(",")]

    return service.get_multi_metric_trend(
        user_id=user_id,
        metric_types=metric_types_list,
        activity_type=activity_type,
        distance_bucket=distance_bucket,
        start_date=start_date,
        end_date=end_date,
        aggregation=aggregation,
        route_id=route_id
    )


@router.get("/percentiles")
async def get_percentile_bands(
    metric_type: str,
    activity_type: str,
    distance_bucket: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    route_id: Optional[int] = None,
    percentiles: str = Query("10,50,90", description="Comma-separated percentiles"),
    period: str = Query("weekly", description="Aggregation period (weekly, monthly)"),
    user_id: int = Query(1, description="User ID"),
    db: Session = Depends(get_db)
):
    """Get percentile distribution for a metric over time"""
    service = TrendsService(db)

    percentiles_list = [int(p.strip()) for p in percentiles.split(",")]

    return service.get_percentile_bands(
        user_id=user_id,
        metric_type=metric_type,
        activity_type=activity_type,
        distance_bucket=distance_bucket,
        start_date=start_date,
        end_date=end_date,
        period=period,
        percentiles=percentiles_list,
        route_id=route_id
    )
