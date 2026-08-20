"""
Effort analysis service for heart rate zone classification.
Uses a fixed 5-zone model based on percentage of max HR.
"""
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from models.activity import Activity
from models.activity_stream import ActivityStream
from models.effort_group import EffortGroup
from models.user import User


class EffortClassifier:
    """Classify effort based on heart rate zones and distance"""
    
    # Fixed 5-zone model (percentage of max HR)
    ZONES = {
        'easy': {'min': 0.50, 'max': 0.60, 'label': 'Zone 1 - Easy'},
        'moderate': {'min': 0.60, 'max': 0.70, 'label': 'Zone 2 - Moderate'},
        'threshold': {'min': 0.70, 'max': 0.80, 'label': 'Zone 3 - Threshold'},
        'vo2max': {'min': 0.80, 'max': 0.90, 'label': 'Zone 4 - VO2 Max'},
        'anaerobic': {'min': 0.90, 'max': 1.00, 'label': 'Zone 5 - Anaerobic'},
    }
    
    # Distance buckets (in meters) - ranges capture typical workout distances
    DISTANCE_BUCKETS = [
        ('5K', 4000, 6000),
        ('10K', 8000, 12000),
        ('Half', 18000, 24000),
        ('Marathon', 38000, 46000),
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_max_hr(self, user_id: int, activity: Activity) -> Optional[int]:
        """
        Determine max HR for zone calculation.
        
        Priority:
        1. User's configured max_hr (if set)
        2. Max HR detected from activity data
        
        Args:
            user_id: User ID
            activity: Activity to analyze
        
        Returns:
            Max HR value, or None if not available
        """
        # Check if user has configured max HR
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.max_hr:
            return user.max_hr
        
        # Fall back to activity's max HR
        if activity.max_heartrate:
            return int(activity.max_heartrate)
        
        # Try to detect from HR stream
        hr_stream = self.db.query(ActivityStream).filter(
            ActivityStream.activity_id == activity.id,
            ActivityStream.stream_type == 'heartrate'
        ).first()
        
        if hr_stream and hr_stream.data:
            return max(hr_stream.data)
        
        return None
    
    def classify_hr_value(self, hr: int, max_hr: int) -> str:
        """
        Classify a single HR value into a zone.
        
        Args:
            hr: Heart rate value (bpm)
            max_hr: Maximum heart rate
        
        Returns:
            Zone name ('easy', 'moderate', 'threshold', 'vo2max', 'anaerobic')
        """
        percentage = hr / max_hr
        
        for zone_name, zone_bounds in self.ZONES.items():
            if zone_bounds['min'] <= percentage < zone_bounds['max']:
                return zone_name
        
        # Handle edge cases
        if percentage < self.ZONES['easy']['min']:
            return 'easy'  # Below zone 1
        else:
            return 'anaerobic'  # Above zone 5
    
    def calculate_time_in_zones(
        self, 
        hr_stream: List[int], 
        max_hr: int,
        time_per_sample: float = 1.0
    ) -> Dict[str, float]:
        """
        Calculate time spent in each HR zone.
        
        Args:
            hr_stream: List of HR values (one per time sample)
            max_hr: Maximum heart rate
            time_per_sample: Seconds per sample (default 1.0 for 1Hz data)
        
        Returns:
            Dict mapping zone name to seconds spent in that zone
        """
        zone_times = {zone: 0.0 for zone in self.ZONES.keys()}
        
        for hr in hr_stream:
            zone = self.classify_hr_value(hr, max_hr)
            zone_times[zone] += time_per_sample
        
        return zone_times
    
    def classify_distance(self, distance_meters: Optional[float]) -> str:
        """
        Classify activity distance into a bucket.
        
        Args:
            distance_meters: Distance in meters
        
        Returns:
            Bucket label ('5K', '10K', 'Half', 'Marathon', or 'Other')
        """
        if not distance_meters or distance_meters <= 0:
            return 'Other'
        
        for bucket_name, min_dist, max_dist in self.DISTANCE_BUCKETS:
            if min_dist <= distance_meters <= max_dist:
                return bucket_name
        
        return 'Other'
    
    def analyze_activity(self, activity_id: int) -> Optional[Dict]:
        """
        Analyze an activity and create effort_group records.
        
        Args:
            activity_id: Activity ID to analyze
        
        Returns:
            Dict with zone breakdown, or None if no HR data
        """
        activity = self.db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            return None
        
        # Get max HR
        max_hr = self.get_max_hr(activity.user_id, activity)
        if not max_hr:
            return None
        
        # Get HR stream
        hr_stream_record = self.db.query(ActivityStream).filter(
            ActivityStream.activity_id == activity_id,
            ActivityStream.stream_type == 'heartrate'
        ).first()
        
        if not hr_stream_record or not hr_stream_record.data:
            return None
        
        hr_stream = hr_stream_record.data
        
        # Calculate time in zones
        zone_times = self.calculate_time_in_zones(hr_stream, max_hr)
        
        # Determine overall effort zone (zone with most time)
        dominant_zone = max(zone_times, key=lambda z: zone_times[z])
        
        # Update activity's effort_zone
        activity.effort_zone = dominant_zone
        
        # Classify and set distance bucket
        if activity.distance:
            activity.distance_bucket = self.classify_distance(activity.distance)
        
        # Delete existing effort_group records for this activity
        self.db.query(EffortGroup).filter(
            EffortGroup.activity_id == activity_id
        ).delete()
        
        # Create new effort_group records
        for zone_name, time_seconds in zone_times.items():
            if time_seconds > 0:
                effort_group = EffortGroup(
                    user_id=activity.user_id,
                    activity_id=activity_id,
                    group_type='hr_zone',
                    group_label=zone_name,
                    time_in_zone=time_seconds
                )
                self.db.add(effort_group)
        
        self.db.commit()
        
        # Calculate percentages
        total_time = sum(zone_times.values())
        zone_percentages = {
            zone: (time / total_time * 100) if total_time > 0 else 0
            for zone, time in zone_times.items()
        }
        
        return {
            'max_hr': max_hr,
            'dominant_zone': dominant_zone,
            'zone_times': zone_times,
            'zone_percentages': zone_percentages,
            'total_time': total_time
        }
    
    def get_activity_effort(self, activity_id: int) -> Optional[Dict]:
        """
        Get effort breakdown for an activity.
        
        Args:
            activity_id: Activity ID
        
        Returns:
            Dict with zone breakdown, or None if not analyzed
        """
        activity = self.db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            return None
        
        # Get effort_group records
        effort_groups = self.db.query(EffortGroup).filter(
            EffortGroup.activity_id == activity_id
        ).all()
        
        if not effort_groups:
            return None
        
        # Get max HR
        max_hr = self.get_max_hr(activity.user_id, activity)
        
        # Build zone breakdown
        zone_times = {eg.group_label: eg.time_in_zone for eg in effort_groups}
        total_time = sum(zone_times.values())
        
        zone_percentages = {
            zone: (time / total_time * 100) if total_time > 0 else 0
            for zone, time in zone_times.items()
        }
        
        return {
            'max_hr': max_hr,
            'dominant_zone': activity.effort_zone,
            'zone_times': zone_times,
            'zone_percentages': zone_percentages,
            'total_time': total_time,
            'zone_labels': {zone: info['label'] for zone, info in self.ZONES.items()}
        }
