"""
Service layer for trends analysis

All values returned by this service are in DISPLAY units:
  - average_speed is converted from m/s to pace (min/km)
  - grade_adjusted_pace is already stored as min/km
  - everything else is passed through unchanged

Trend direction and R² are therefore computed on the same values the
frontend renders — no client-side re-statistics needed.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from models.activity import Activity
from models.computed_metric import ComputedMetric
from services.analytics_engine import AnalyticsEngine

# Distance bucket name -> (min_meters, max_meters), inclusive
DISTANCE_BUCKETS = {
    "5k": (4500, 5500),
    "10k": (9000, 11000),
    "half": (20000, 22000),
    "marathon": (40000, 44000),
}

# Unit label for each metric, as returned in the "unit" field
METRIC_UNITS = {
    "average_speed": "min/km",
    "grade_adjusted_pace": "min/km",
    "average_heartrate": "bpm",
    "average_cadence": "spm",
    "total_elevation_gain": "m",
    "distance": "m",
    "hr_pace_ratio": "",
    "heart_rate_drift": "%",
}


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
        aggregation: Optional[str] = None,
        route_id: Optional[int] = None
    ) -> dict:
        """
        Get trend metrics for a specific metric type (in display units).

        Args:
            user_id: User ID
            metric_type: Metric column on Activity, or a computed metric
                (hr_pace_ratio, grade_adjusted_pace, heart_rate_drift)
            activity_type: Optional activity type filter
            distance_bucket: Optional distance bucket filter (5k, 10k, half, marathon)
            start_date: Optional start date filter
            end_date: Optional end date filter
            aggregation: Aggregation period (daily, weekly, monthly)
            route_id: Optional route filter — only activities on this route

        Returns:
            Dictionary with data_points, aggregated_data, trend and the metric's
            display unit. Pace metrics carry min/km values and "min/km" unit.
        """
        period = aggregation if aggregation else "weekly"
        computed_metric_types = ["hr_pace_ratio", "grade_adjusted_pace", "running_economy", "heart_rate_drift"]

        if metric_type in computed_metric_types:
            triples = self._query_computed_metric(
                user_id=user_id,
                metric_type=metric_type,
                activity_type=activity_type,
                distance_bucket=distance_bucket,
                start_date=start_date,
                end_date=end_date,
                route_id=route_id,
            )
        else:
            triples = self._query_activity_metric(
                user_id=user_id,
                metric_type=metric_type,
                activity_type=activity_type,
                distance_bucket=distance_bucket,
                start_date=start_date,
                end_date=end_date,
                route_id=route_id,
            )

        return self._build_trend_response(
            metric_type=metric_type,
            period=period,
            activity_type=activity_type,
            triples=triples,
        )

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def _query_activity_metric(
        self,
        user_id: int,
        metric_type: str,
        activity_type: Optional[str],
        distance_bucket: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        route_id: Optional[int] = None,
    ) -> List[tuple]:
        """Fetch (date, raw_value, activity_id) triples for a metric stored on Activity."""
        query = self.db.query(Activity).filter(Activity.user_id == user_id)

        if activity_type:
            query = query.filter(Activity.type == activity_type)
        if route_id:
            query = query.filter(Activity.route_id == route_id)
        query = self._apply_date_filters(query, start_date, end_date, Activity.start_date)
        query = self._apply_distance_bucket(query, distance_bucket, Activity.distance)
        query = query.order_by(Activity.start_date)

        triples = []
        for activity in query.all():
            value = getattr(activity, metric_type, None)
            if value is not None:
                triples.append((activity.start_date, float(value), activity.id))
        return triples

    def _query_computed_metric(
        self,
        user_id: int,
        metric_type: str,
        activity_type: Optional[str],
        distance_bucket: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        route_id: Optional[int] = None,
    ) -> List[tuple]:
        """Fetch (date, raw_value, activity_id) triples for a metric stored in ComputedMetric."""
        query = self.db.query(ComputedMetric, Activity).join(
            Activity, ComputedMetric.activity_id == Activity.id
        ).filter(
            ComputedMetric.user_id == user_id,
            ComputedMetric.metric_type == metric_type
        )

        if activity_type:
            query = query.filter(Activity.type == activity_type)
        if route_id:
            query = query.filter(Activity.route_id == route_id)
        query = self._apply_date_filters(query, start_date, end_date, Activity.start_date)
        query = self._apply_distance_bucket(query, distance_bucket, Activity.distance)
        query = query.order_by(Activity.start_date)

        return [
            (activity.start_date, float(metric.value), activity.id)
            for metric, activity in query.all()
        ]

    @staticmethod
    def _apply_date_filters(query, start_date: Optional[datetime], end_date: Optional[datetime], column):
        if start_date:
            query = query.filter(column >= start_date)
        if end_date:
            query = query.filter(column <= end_date)
        return query

    @staticmethod
    def _apply_distance_bucket(query, distance_bucket: Optional[str], column):
        """Apply case-insensitive distance bucket filter (5k/10k/half/marathon)."""
        if distance_bucket:
            bucket_key = distance_bucket.lower()
            if bucket_key in DISTANCE_BUCKETS:
                min_dist, max_dist = DISTANCE_BUCKETS[bucket_key]
                query = query.filter(column >= min_dist, column <= max_dist)
        return query

    # ------------------------------------------------------------------
    # Response assembly
    # ------------------------------------------------------------------

    def _build_trend_response(
        self,
        metric_type: str,
        period: str,
        activity_type: Optional[str],
        triples: List[tuple],
    ) -> dict:
        """
        Convert raw values to display units, then compute trend / aggregation /
        percentiles on the converted values (single source of truth).
        """
        unit = self.metric_unit(metric_type)
        empty = {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "unit": unit,
            "data_points": [],
            "aggregated_data": [],
            "trend": {"slope": 0, "direction": "stable", "r_squared": 0},
            "percentiles": []
        }

        if not triples:
            return empty

        dates = [d for d, _, _ in triples]
        # Convert to display units BEFORE statistics (pace is a non-linear
        # transform, so stats must run on converted values)
        values = [self.engine.to_display_value(metric_type, v) for _, v, _ in triples]

        trend = self.engine.calculate_trend(dates, values, metric_type=metric_type)
        aggregated = self.engine.aggregate_by_period(dates, values, period)
        percentiles = self.engine.calculate_percentiles(dates, values, period=period)

        data_points = [
            {"date": d, "value": v, "activity_id": aid}
            for (d, _, aid), v in zip(triples, values)
        ]

        return {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "unit": unit,
            "data_points": data_points,
            "aggregated_data": aggregated,
            "trend": trend,
            "percentiles": percentiles
        }

    @staticmethod
    def metric_unit(metric_type: str) -> str:
        """Display unit label for a metric type."""
        return METRIC_UNITS.get(metric_type, "")

    def get_multi_metric_trend(
        self,
        user_id: int,
        metric_types: List[str],
        activity_type: Optional[str] = None,
        distance_bucket: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[str] = None,
        route_id: Optional[int] = None
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
                aggregation=aggregation,
                route_id=route_id
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
        percentiles: List[int] = [10, 50, 90],
        route_id: Optional[int] = None
    ) -> dict:
        """
        Get percentile distribution for a metric over time

        Returns:
            Dictionary with percentile bands
        """
        trend_data = self.get_metric_trend(
            user_id=user_id,
            metric_type=metric_type,
            activity_type=activity_type,
            distance_bucket=distance_bucket,
            start_date=start_date,
            end_date=end_date,
            aggregation=period,
            route_id=route_id
        )

        return {
            "metric_type": metric_type,
            "activity_type": activity_type,
            "period": period,
            "unit": self.metric_unit(metric_type),
            "percentiles": percentiles,
            "bands": trend_data.get("percentiles", [])
        }

    def get_available_metrics(self, user_id: int) -> List[str]:
        """
        Get list of available metrics for a user

        Returns:
            List of metric type strings
        """
        # Standard activity metrics (names match Activity columns / API names)
        metrics = ["average_speed", "average_heartrate", "average_cadence", "distance", "moving_time", "total_elevation_gain"]

        # Check for computed metrics
        computed_metrics = self.db.query(ComputedMetric.metric_type).filter(
            ComputedMetric.user_id == user_id
        ).distinct().all()

        computed_metric_types = [m[0] for m in computed_metrics]

        return metrics + computed_metric_types
