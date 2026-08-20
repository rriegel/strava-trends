"""
Service layer for trends analysis
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.activity import Activity
from models.computed_metric import ComputedMetric
from services.analytics_engine import AnalyticsEngine


class TrendsService:
    """Service layer for trends analysis"""
    
    def __init__(self, db: Session):
        self.db = db
        self.engine = AnalyticsEngine()
    
    def get_metric_trend(
        self,
        user_id: int,
        metric_type: str,
        activity_type: Optional[str] = None,
        distance_bucket: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[str] = None
    ) -> dict:
        """
        Get trend metrics for a specific metric type
        
        Args:
            user_id: User ID
            metric_type: Type of metric (avg_speed, avg_heartrate, distance, moving_time, total_elevation_gain)
            activity_type: Optional activity type filter
            distance_bucket: Optional distance bucket filter (e.g., "5k", "10k", "half")
            start_date: Optional start date filter
            end_date: Optional end date filter
            aggregation: Aggregation period (daily, weekly, monthly)
        
        Returns:
            Dictionary with trend data
        """
        # Map aggregation to period for the engine
        period = aggregation if aggregation else "weekly"
        
        # Check if this is a computed metric
        computed_metric_types = ["hr_pace_ratio", "grade_adjusted_pace", "running_economy", "heart_rate_drift"]
        is_computed_metric = metric_type in computed_metric_types
        
        if is_computed_metric:
            return self._get_computed_metric_trend(
                user_id=user_id,
                metric_type=metric_type,
                activity_type=activity_type,
                distance_bucket=distance_bucket,
                start_date=start_date,
                end_date=end_date,
                period=period
            )
        
        # Build query for activities
        query = self.db.query(Activity).filter(Activity.user_id == user_id)
        
        # Apply filters
        if activity_type:
            query = query.filter(Activity.type == activity_type)
        if start_date:
            query = query.filter(Activity.start_date >= start_date)
        if end_date:
            query = query.filter(Activity.start_date <= end_date)
        
        # Distance bucket filter
        if distance_bucket:
            # Convert distance_bucket to meters for filtering (case-insensitive)
            bucket_ranges = {
                "5k": (4500, 5500),
                "10k": (9000, 11000),
                "half": (20000, 22000),
                "marathon": (40000, 44000)
            }
            bucket_key = distance_bucket.lower()
            if bucket_key in bucket_ranges:
                min_dist, max_dist = bucket_ranges[bucket_key]
                query = query.filter(Activity.distance >= min_dist, Activity.distance <= max_dist)
        
        # Order by date
        query = query.order_by(Activity.start_date)
        
        # Get activities
        activities = query.all()
        
        # Extract data points
        dates = []
        values = []
        activity_ids = []
        
        for activity in activities:
            value = getattr(activity, metric_type, None)
            if value is not None:
                dates.append(activity.start_date)
                values.append(float(value))
                activity_ids.append(activity.id)
        
        if not dates:
            return {
                "metric_type": metric_type,
                "activity_type": activity_type,
                "period": period,
                "data_points": [],
                "aggregated_data": [],
                "trend": {"slope": 0, "direction": "stable", "r_squared": 0},
                "percentiles": []
            }
        
        # Calculate trend
        trend = self.engine.calculate_trend(dates, values)
        
        # Aggregate by period
        aggregated = self.engine.aggregate_by_period(dates, values, period)
        
        # Calculate percentiles
        percentiles = self.engine.calculate_percentiles(dates, values, period=period)
        
        # Build data points
        data_points = [
            {"date": d, "value": v, "activity_id": aid}
            for d, v, aid in zip(dates, values, activity_ids)
        ]
        
        return {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "data_points": data_points,
            "aggregated_data": aggregated,
            "trend": trend,
            "percentiles": percentiles
        }
    
    def _get_computed_metric_trend(
        self,
        user_id: int,
        metric_type: str,
        activity_type: Optional[str] = None,
        distance_bucket: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "weekly"
    ) -> dict:
        """
        Get trend for computed metrics (hr_pace_ratio, grade_adjusted_pace, etc.)
        """
        # Build query for computed metrics joined with activities
        query = self.db.query(ComputedMetric, Activity).join(
            Activity, ComputedMetric.activity_id == Activity.id
        ).filter(
            ComputedMetric.user_id == user_id,
            ComputedMetric.metric_type == metric_type
        )
        
        # Apply filters
        if activity_type:
            query = query.filter(Activity.type == activity_type)
        if start_date:
            query = query.filter(Activity.start_date >= start_date)
        if end_date:
            query = query.filter(Activity.start_date <= end_date)
        
        # Distance bucket filter
        if distance_bucket:
            bucket_ranges = {
                "5k": (4500, 5500),
                "10k": (9000, 11000),
                "half": (20000, 22000),
                "marathon": (40000, 44000)
            }
            bucket_key = distance_bucket.lower()
            if bucket_key in bucket_ranges:
                min_dist, max_dist = bucket_ranges[bucket_key]
                query = query.filter(Activity.distance >= min_dist, Activity.distance <= max_dist)
        
        # Order by date
        query = query.order_by(Activity.start_date)
        
        # Get metrics
        results = query.all()
        
        # Extract data points
        dates = []
        values = []
        activity_ids = []
        
        for metric, activity in results:
            dates.append(activity.start_date)
            values.append(float(metric.value))
            activity_ids.append(activity.id)
        
        if not dates:
            return {
                "metric_type": metric_type,
                "activity_type": activity_type,
                "period": period,
                "data_points": [],
                "aggregated_data": [],
                "trend": {"slope": 0, "direction": "stable", "r_squared": 0},
                "percentiles": []
            }
        
        # Calculate trend
        trend = self.engine.calculate_trend(dates, values)
        
        # Aggregate by period
        aggregated = self.engine.aggregate_by_period(dates, values, period)
        
        # Calculate percentiles
        percentiles = self.engine.calculate_percentiles(dates, values, period=period)
        
        # Build data points
        data_points = [
            {"date": d, "value": v, "activity_id": aid}
            for d, v, aid in zip(dates, values, activity_ids)
        ]
        
        return {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "data_points": data_points,
            "aggregated_data": aggregated,
            "trend": trend,
            "percentiles": percentiles
        }
    
    def get_multi_metric_trend(
        self,
        user_id: int,
        metric_types: List[str],
        activity_type: Optional[str] = None,
        distance_bucket: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[str] = None
    ) -> dict:
        """
        Get trend data for multiple metrics simultaneously
        
        Returns:
            Dictionary with 'metrics' key containing metric_type as key and trend data as value
        """
        results = {}
        for metric_type in metric_types:
            results[metric_type] = self.get_metric_trend(
                user_id=user_id,
                metric_type=metric_type,
                activity_type=activity_type,
                distance_bucket=distance_bucket,
                start_date=start_date,
                end_date=end_date,
                aggregation=aggregation
            )
        
        return {"metrics": results}
    
    def get_percentile_bands(
        self,
        user_id: int,
        metric_type: str,
        activity_type: str,
        distance_bucket: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "weekly",
        percentiles: List[int] = [10, 50, 90]
    ) -> dict:
        """
        Get percentile distribution for a metric over time
        
        Returns:
            Dictionary with percentile bands
        """
        # Get the trend data
        trend_data = self.get_metric_trend(
            user_id=user_id,
            metric_type=metric_type,
            activity_type=activity_type,
            distance_bucket=distance_bucket,
            start_date=start_date,
            end_date=end_date,
            aggregation=period
        )
        
        # Extract percentile bands from the trend data
        return {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "percentiles": percentiles,
            "bands": trend_data.get("percentiles", [])
        }
    
    def get_available_metrics(self, user_id: int) -> List[str]:
        """
        Get list of available metrics for a user
        
        Returns:
            List of metric type strings
        """
        # Standard activity metrics
        metrics = ["avg_speed", "avg_heartrate", "distance", "moving_time", "total_elevation_gain"]
        
        # Check for computed metrics
        computed_metrics = self.db.query(ComputedMetric.metric_type).filter(
            ComputedMetric.user_id == user_id
        ).distinct().all()
        
        computed_metric_types = [m[0] for m in computed_metrics]
        
        return metrics + computed_metric_types
