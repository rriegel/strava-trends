"""
Service for computing and storing derived metrics from activity data.
"""
from sqlalchemy.orm import Session
from models.activity import Activity
from models.computed_metric import ComputedMetric
from services.analytics_engine import AnalyticsEngine


class ComputedMetricsService:
    """Compute and store derived metrics for activities"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_metrics_for_activity(self, activity_id: int) -> int:
        """
        Compute all derived metrics for an activity and store them.
        
        Returns the number of metrics computed.
        """
        activity = self.db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            return 0
        
        metrics_computed = 0
        
        # Only compute for running activities
        if activity.type not in ['Run', 'TrailRun', 'VirtualRun']:
            return 0
        
        # Need HR and speed data for most metrics
        if not activity.has_heartrate or not activity.average_speed:
            return 0
        
        # Convert speed (m/s) to pace (min/km) for running metrics
        avg_pace_min_per_km = AnalyticsEngine.speed_to_pace(float(activity.average_speed))
        
        # 1. HR/Pace Ratio (HR per min/km)
        if activity.average_heartrate and avg_pace_min_per_km > 0:
            hr_pace_ratio = AnalyticsEngine.compute_hr_pace_ratio(
                float(activity.average_heartrate),
                avg_pace_min_per_km
            )
            self._store_metric(activity, 'hr_pace_ratio', hr_pace_ratio)
            metrics_computed += 1
        
        # 2. Grade Adjusted Pace (GAP)
        if activity.average_speed and activity.total_elevation_gain and activity.distance:
            # Convert speed to pace
            pace = avg_pace_min_per_km
            gap = AnalyticsEngine.compute_grade_adjusted_pace(
                pace,
                float(activity.total_elevation_gain),
                float(activity.distance)
            )
            self._store_metric(activity, 'grade_adjusted_pace', gap)
            metrics_computed += 1
        
        # 3. Heart Rate Drift
        # Need HR stream data to compute first/second half HR
        from models.activity_stream import ActivityStream
        hr_stream = self.db.query(ActivityStream).filter(
            ActivityStream.activity_id == activity_id,
            ActivityStream.stream_type == 'heartrate'
        ).first()
        
        if hr_stream and hr_stream.data and len(hr_stream.data) >= 10:
            # Split HR data into first and second half
            midpoint = len(hr_stream.data) // 2
            first_half = hr_stream.data[:midpoint]
            second_half = hr_stream.data[midpoint:]
            
            # Filter out zeros (resting periods)
            first_half_valid = [hr for hr in first_half if hr > 0]
            second_half_valid = [hr for hr in second_half if hr > 0]
            
            if first_half_valid and second_half_valid:
                first_half_avg = sum(first_half_valid) / len(first_half_valid)
                second_half_avg = sum(second_half_valid) / len(second_half_valid)
                
                drift = AnalyticsEngine.compute_heart_rate_drift(
                    first_half_avg,
                    second_half_avg
                )
                self._store_metric(activity, 'heart_rate_drift', drift)
                metrics_computed += 1
        
        # 4. Running Economy (optional, needs weight)
        # Skipping for now since we don't have user weight data
        
        self.db.commit()
        return metrics_computed
    
    def _store_metric(self, activity: Activity, metric_type: str, value: float):
        """Store or update a computed metric"""
        # Check if metric already exists
        existing = self.db.query(ComputedMetric).filter(
            ComputedMetric.user_id == activity.user_id,
            ComputedMetric.activity_id == activity.id,
            ComputedMetric.metric_type == metric_type
        ).first()
        
        if existing:
            existing.value = value
        else:
            metric = ComputedMetric(
                user_id=activity.user_id,
                activity_id=activity.id,
                metric_type=metric_type,
                value=value
            )
            self.db.add(metric)
