"""
File upload service for parsing FIT, GPX, and TCX activity files.
Source-agnostic: works with any device that exports these formats.
"""
import os
import tempfile
from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session

from models.activity import Activity
from models.activity_stream import ActivityStream
from models.user import User


class FileUploadService:
    """Parse and import activity files (FIT, GPX, TCX)"""
    
    SUPPORTED_FORMATS = {'.fit', '.gpx', '.tcx'}
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_upload(self, user_id: int, file_content: bytes, filename: str) -> Dict:
        """
        Process an uploaded activity file.
        
        Args:
            user_id: User who owns the activity
            file_content: Raw file bytes
            filename: Original filename (used for format detection and source_id)
        
        Returns:
            Dict with status and activity info
        """
        # Validate file format
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}")
        
        # Parse file based on format
        if ext == '.fit':
            activity_data = self._parse_fit(file_content)
        elif ext == '.gpx':
            activity_data = self._parse_gpx(file_content)
        elif ext == '.tcx':
            activity_data = self._parse_tcx(file_content)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        # Check for duplicates (same source + source_id)
        source_id = f"{filename}_{activity_data.get('start_date', '').isoformat()}"
        existing = self.db.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.source == "file_upload",
            Activity.source_id == source_id
        ).first()
        
        if existing:
            return {
                "status": "duplicate",
                "message": "Activity already exists",
                "activity_id": existing.id
            }
        
        # Filter out internal keys (prefixed with _) before passing to Activity
        activity_data_clean = {k: v for k, v in activity_data.items() if not k.startswith('_')}
        
        # Create new activity
        activity = Activity(
            user_id=user_id,
            source="file_upload",
            source_id=source_id,
            **activity_data_clean
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        # Save latlng stream if we have route data
        if activity_data.get('_latlng_stream'):
            stream = ActivityStream(
                user_id=user_id,
                activity_id=activity.id,
                stream_type='latlng',
                data=activity_data['_latlng_stream'],
                series_type='time',
                original_size=len(activity_data['_latlng_stream'])
            )
            self.db.add(stream)
            
            # Save altitude stream too
            if activity_data.get('_altitude_stream'):
                alt_stream = ActivityStream(
                    user_id=user_id,
                    activity_id=activity.id,
                    stream_type='altitude',
                    data=activity_data['_altitude_stream'],
                    series_type='time',
                    original_size=len(activity_data['_altitude_stream'])
                )
                self.db.add(alt_stream)
            
            activity.has_streams = True
            self.db.commit()
        
        # Save HR stream if present
        if activity_data.get('_hr_stream'):
            hr_stream = ActivityStream(
                user_id=user_id,
                activity_id=activity.id,
                stream_type='heartrate',
                data=activity_data['_hr_stream'],
                series_type='time',
                original_size=len(activity_data['_hr_stream'])
            )
            self.db.add(hr_stream)
            activity.has_streams = True
            self.db.commit()
            
            # Analyze effort zones if we have HR data
            from services.effort_classifier import EffortClassifier
            classifier = EffortClassifier(self.db)
            classifier.analyze_activity(activity.id)
        else:
            # Even without HR data, classify distance
            from services.effort_classifier import EffortClassifier
            classifier = EffortClassifier(self.db)
            if activity.distance:
                activity.distance_bucket = classifier.classify_distance(activity.distance)
                self.db.commit()
        
        return {
            "status": "success",
            "activity_id": activity.id,
            "activity_name": activity.name,
            "activity_type": activity.type,
            "start_date": activity.start_date.isoformat() if activity.start_date else None,
            "has_streams": activity.has_streams or False
        }
    
    def _parse_fit(self, file_content: bytes) -> Dict:
        """Parse FIT file using fitparse"""
        try:
            import fitparse
        except ImportError:
            raise ImportError("fitparse not installed. Add python-fitparse to requirements.")
        
        # Write to temp file (fitparse needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.fit') as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            fit_file = fitparse.FitFile(tmp_path)
            fit_file.parse()
            
            # Extract session data (summary)
            session = None
            for record in fit_file.get_messages('session'):
                session = record
                break
            
            if not session:
                raise ValueError("No session data found in FIT file")
            
            # DEBUG: Log all available fields
            import logging
            logger = logging.getLogger(__name__)
            available_fields = []
            for field in session.fields:
                available_fields.append(f"{field.name}: {field.value}")
            logger.info(f"FIT file session fields: {available_fields}")
            
            # Collect HR stream from record messages
            hr_stream = []
            for record in fit_file.get_messages('record'):
                hr = self._get_field(record, 'heart_rate')
                if hr is not None:
                    hr_stream.append(hr)
            
            # Map FIT fields to our schema
            # Try start_time first, fall back to timestamp if not found
            start_time = self._get_field(session, 'start_time') or self._get_field(session, 'timestamp')
            
            data = {
                "name": self._get_field(session, 'event') or "FIT Activity",
                "type": self._map_fit_sport(self._get_field(session, 'sport')),
                "sport_type": self._get_field(session, 'sub_sport'),
                "start_date": start_time,
                "start_date_local": start_time,
                "moving_time": self._get_field(session, 'total_timer_time'),
                "elapsed_time": self._get_field(session, 'total_elapsed_time'),
                "distance": self._get_field(session, 'total_distance'),
                "total_elevation_gain": self._get_field(session, 'total_ascent'),
                "average_speed": self._get_field(session, 'enhanced_avg_speed') or self._get_field(session, 'avg_speed'),
                "max_speed": self._get_field(session, 'enhanced_max_speed') or self._get_field(session, 'max_speed'),
                "average_heartrate": self._get_field(session, 'avg_heart_rate'),
                "max_heartrate": self._get_field(session, 'max_heart_rate'),
                "has_heartrate": self._get_field(session, 'avg_heart_rate') is not None,
                "average_cadence": self._get_field(session, 'avg_cadence'),
                "average_watts": self._get_field(session, 'avg_power'),
                "max_watts": self._get_field(session, 'max_power'),
                "_hr_stream": hr_stream if hr_stream else None,
            }
            
            # Clean up None values and convert types
            return self._clean_activity_data(data)
        
        finally:
            os.unlink(tmp_path)
    
    def _parse_gpx(self, file_content: bytes) -> Dict:
        """Parse GPX file using gpxpy"""
        try:
            import gpxpy
        except ImportError:
            raise ImportError("gpxpy not installed. Add gpxpy to requirements.")
        
        gpx = gpxpy.parse(file_content.decode('utf-8'))
        
        if not gpx.tracks:
            raise ValueError("No tracks found in GPX file")
        
        track = gpx.tracks[0]
        
        # Calculate summary stats with improved accuracy
        total_distance = 0
        moving_time = 0
        elapsed_time = 0
        max_speed = 0
        hr_values = []
        cadence_values = []
        elevation_points = []  # Collect for moving average smoothing
        
        # Thresholds for filtering GPS noise
        SPEED_THRESHOLD = 0.5  # m/s - consider stationary below this speed
        ELEVATION_WINDOW = 5  # Moving average window size for elevation smoothing
        
        # Collect route data for map visualization
        latlng_stream = []
        altitude_stream = []
        hr_stream = []
        
        for segment in track.segments:
            for i, point in enumerate(segment.points):
                # Collect latlng for route map
                if point.latitude is not None and point.longitude is not None:
                    latlng_stream.append([point.latitude, point.longitude])
                
                # Collect elevation data for smoothing
                if point.elevation is not None:
                    elevation_points.append(point.elevation)
                    altitude_stream.append(point.elevation)
                
                if i > 0 and segment.points[i-1]:
                    prev = segment.points[i-1]
                    
                    # Distance: use 2D (horizontal only) to avoid GPS elevation noise
                    distance = point.distance_2d(prev) or 0
                    total_distance += distance
                    
                    # Time and speed calculations
                    if point.time and prev.time:
                        time_diff = (point.time - prev.time).total_seconds()
                        elapsed_time += time_diff
                        
                        # Calculate speed and determine if moving
                        if time_diff > 0 and distance > 0:
                            speed = distance / time_diff
                            max_speed = max(max_speed, speed)
                            
                            # Only count time if speed exceeds threshold (moving)
                            if speed >= SPEED_THRESHOLD:
                                moving_time += time_diff
                
                # Extract HR/cadence from extensions (Garmin gpxtpx namespace)
                if point.extensions:
                    hr_val = self._extract_gpx_extension(point, 'hr')
                    cad_val = self._extract_gpx_extension(point, 'cad')
                    
                    if hr_val is not None:
                        hr_values.append(hr_val)
                        hr_stream.append(hr_val)
                    if cad_val is not None:
                        cadence_values.append(cad_val)
        
        # Apply moving average smoothing to elevation data to reduce GPS noise
        total_elevation = self._calculate_elevation_gain(elevation_points, ELEVATION_WINDOW)
        
        # Get start/end time
        start_time = None
        for segment in track.segments:
            if segment.points:
                start_time = segment.points[0].time
                break
        
        avg_speed = total_distance / moving_time if moving_time > 0 else 0
        
        data = {
            "_latlng_stream": latlng_stream if latlng_stream else None,
            "_altitude_stream": altitude_stream if altitude_stream else None,
            "_hr_stream": hr_stream if hr_stream else None,
            "name": track.name or "GPX Activity",
            "type": "Run",  # GPX doesn't always specify sport; default to Run
            "sport_type": None,
            "start_date": start_time,
            "start_date_local": start_time,
            "moving_time": int(moving_time),
            "elapsed_time": int(elapsed_time),
            "distance": total_distance,
            "total_elevation_gain": total_elevation,
            "average_speed": avg_speed,
            "max_speed": max_speed,
            "average_heartrate": sum(hr_values) / len(hr_values) if hr_values else None,
            "max_heartrate": max(hr_values) if hr_values else None,
            "has_heartrate": len(hr_values) > 0,
            "average_cadence": sum(cadence_values) / len(cadence_values) if cadence_values else None,
        }
        
        return self._clean_activity_data(data)
    
    def _calculate_elevation_gain(self, elevation_points: list, window: int = 5) -> float:
        """Calculate elevation gain using hysteresis/peak detection to reduce GPS noise.
        
        This approach tracks elevation peaks and only counts gain when climbing
        above a previous low point by a meaningful threshold, reducing false
        positives from GPS drift.
        
        Args:
            elevation_points: List of elevation values in order
            window: Moving average window size for initial smoothing (default 5)
        
        Returns:
            Total elevation gain in meters
        """
        if len(elevation_points) < 2:
            return 0.0
        
        # Step 1: Apply moving average smoothing to reduce high-frequency noise
        smoothed = []
        for i in range(len(elevation_points)):
            start = max(0, i - window // 2)
            end = min(len(elevation_points), i + window // 2 + 1)
            window_points = elevation_points[start:end]
            smoothed.append(sum(window_points) / len(window_points))
        
        # Step 2: Hysteresis/peak detection
        # Only count elevation gain when we climb above a valley by a threshold
        MIN_GAIN_THRESHOLD = 2.0  # meters - minimum climb to count as real elevation gain
        
        total_gain = 0.0
        valley = smoothed[0]  # Track the lowest point since last peak
        
        for i in range(1, len(smoothed)):
            current = smoothed[i]
            
            # If we've climbed above the valley by the threshold, count the gain
            if current >= valley + MIN_GAIN_THRESHOLD:
                total_gain += (current - valley)
                valley = current  # Reset valley to current peak
            elif current < valley:
                # We're descending, update the valley
                valley = current
        
        return total_gain
    
    def _extract_gpx_extension(self, point, field: str) -> Optional[int]:
        """Extract HR or cadence from GPX trackpoint extensions.
        
        Garmin devices use the gpxtpx namespace for TrackPointExtension data.
        
        Args:
            point: GPX trackpoint object
            field: 'hr' for heart rate, 'cad' for cadence
        
        Returns:
            Integer value if found, None otherwise
        """
        try:
            # GPX extensions are in the TrackPointExtension namespace
            gpxtpx_ns = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
            
            for ext in point.extensions:
                # Look for TrackPointExtension element
                if ext.tag == f'{{{gpxtpx_ns}}}TrackPointExtension':
                    # Find the requested field (hr or cad)
                    field_elem = ext.find(f'{{{gpxtpx_ns}}}{field}')
                    if field_elem is not None and field_elem.text:
                        return int(field_elem.text)
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def _parse_tcx(self, file_content: bytes) -> Dict:
        """Parse TCX file using xml.etree (TCX is XML-based)"""
        import xml.etree.ElementTree as ET
        
        # TCX uses namespaces
        namespaces = {
            'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
            'ext': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
        }
        
        root = ET.fromstring(file_content.decode('utf-8'))
        
        # Find Activity element
        activity = root.find('.//tcx:Activity', namespaces)
        if not activity:
            raise ValueError("No Activity found in TCX file")
        
        sport = activity.get('Sport', 'Running')
        
        # Extract lap data
        total_distance = 0
        total_time = 0
        total_calories = 0
        hr_values = []
        cadence_values = []
        start_time = None
        
        for lap in activity.findall('.//tcx:Lap', namespaces):
            dist_elem = lap.find('tcx:DistanceMeters', namespaces)
            time_elem = lap.find('tcx:TotalTimeSeconds', namespaces)
            cal_elem = lap.find('tcx:Calories', namespaces)
            
            if dist_elem is not None and dist_elem.text:
                total_distance += float(dist_elem.text)
            if time_elem is not None and time_elem.text:
                total_time += float(time_elem.text)
            if cal_elem is not None and cal_elem.text:
                total_calories += int(cal_elem.text)
            
            if not start_time:
                start_time = lap.get('StartTime')
            
            # Extract HR from trackpoints
            for tp in lap.findall('.//tcx:Trackpoint', namespaces):
                hr = tp.find('.//tcx:HeartRateBpm/tcx:Value', namespaces)
                if hr is not None:
                    hr_values.append(int(hr.text))
                
                cad = tp.find('.//tcx:Cadence', namespaces)
                if cad is not None:
                    cadence_values.append(int(cad.text))
        
        avg_speed = total_distance / total_time if total_time > 0 else 0
        
        data = {
            "name": f"{sport} Activity",
            "type": self._map_tcx_sport(sport),
            "sport_type": sport,
            "start_date": datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None,
            "start_date_local": datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None,
            "moving_time": int(total_time),
            "elapsed_time": int(total_time),
            "distance": total_distance,
            "total_elevation_gain": 0,  # TCX doesn't always include elevation summary
            "average_speed": avg_speed,
            "max_speed": avg_speed * 1.2,  # Estimate
            "average_heartrate": sum(hr_values) / len(hr_values) if hr_values else None,
            "max_heartrate": max(hr_values) if hr_values else None,
            "has_heartrate": len(hr_values) > 0,
            "average_cadence": sum(cadence_values) / len(cadence_values) if cadence_values else None,
        }
        
        return self._clean_activity_data(data)
    
    def _get_field(self, record, field_name: str):
        """Safely extract a field from a FIT record"""
        try:
            field = record.get_field(field_name)
            return field.value if field else None
        except:
            return None
    
    def _map_fit_sport(self, sport: Optional[str]) -> str:
        """Map FIT sport names to our activity types"""
        mapping = {
            'running': 'Run',
            'cycling': 'Ride',
            'swimming': 'Swim',
            'walking': 'Walk',
            'hiking': 'Hike',
            'strength_training': 'WeightTraining',
            'yoga': 'Yoga',
        }
        return mapping.get(sport.lower() if sport else '', 'Other')
    
    def _map_tcx_sport(self, sport: str) -> str:
        """Map TCX sport names to our activity types"""
        mapping = {
            'Running': 'Run',
            'Biking': 'Ride',
            'Other': 'Other',
        }
        return mapping.get(sport, 'Other')
    
    def _clean_activity_data(self, data: Dict) -> Dict:
        """Clean and validate activity data"""
        # Remove None values
        cleaned = {k: v for k, v in data.items() if v is not None}
        
        # Ensure required fields
        if 'name' not in cleaned:
            cleaned['name'] = 'Activity'
        if 'type' not in cleaned:
            cleaned['type'] = 'Other'
        if 'start_date' not in cleaned:
            raise ValueError("Activity must have a start_date")
        
        # Convert numeric fields to appropriate types
        numeric_fields = ['moving_time', 'elapsed_time', 'distance', 'total_elevation_gain',
                         'average_speed', 'max_speed', 'average_heartrate', 'max_heartrate',
                         'average_cadence', 'average_watts', 'max_watts']
        
        for field in numeric_fields:
            if field in cleaned and cleaned[field] is not None:
                try:
                    cleaned[field] = float(cleaned[field])
                except (ValueError, TypeError):
                    cleaned[field] = None
        
        return cleaned
