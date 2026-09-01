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
from utils.activity_calculations import (
    calculate_moving_time,
    calculate_max_speed,
    calculate_elevation_gain
)


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
        start_date_str = activity_data.get('start_date', '')
        if hasattr(start_date_str, 'isoformat'):
            start_date_str = start_date_str.isoformat()
        source_id = f"{filename}_{start_date_str}"
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
        
        # Compute derived metrics (HR/Pace Ratio, GAP, HR Drift)
        from services.computed_metrics_service import ComputedMetricsService
        metrics_service = ComputedMetricsService(self.db)
        metrics_service.compute_metrics_for_activity(activity.id)
        
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
            
            # Extract data from record messages (per-second data points)
            latlng_stream = []
            altitude_stream = []
            hr_stream = []
            cadence_stream = []
            altitude_points = []
            hr_values = []
            cadence_values = []
            timestamps = []
            cumulative_distances = []
            
            # Track previous GPS position for cumulative distance
            prev_lat = None
            prev_lon = None
            running_distance = 0.0
            
            for record in fit_file.get_messages('record'):
                # Timestamp - skip entire record if no timestamp
                timestamp = self._get_field(record, 'timestamp')
                if timestamp is None:
                    continue
                timestamps.append(timestamp)
                
                # GPS coordinates
                lat = self._get_field(record, 'position_lat')
                lng = self._get_field(record, 'position_long')
                if lat is not None and lng is not None:
                    # FIT stores lat/lng in semicircles, convert to degrees
                    lat_deg = lat * (180.0 / 2**31)
                    lng_deg = lng * (180.0 / 2**31)
                    latlng_stream.append([lat_deg, lng_deg])
                    
                    # Calculate segment distance from previous GPS point
                    if prev_lat is not None and prev_lon is not None:
                        from math import radians, sin, cos, sqrt, atan2
                        R = 6371000
                        lat1_rad = radians(prev_lat)
                        lat2_rad = radians(lat_deg)
                        delta_lat = radians(lat_deg - prev_lat)
                        delta_lon = radians(lng_deg - prev_lon)
                        
                        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
                        c = 2 * atan2(sqrt(a), sqrt(1 - a))
                        running_distance += R * c
                    
                    prev_lat = lat_deg
                    prev_lon = lng_deg
                
                # Cumulative distance mirrors timestamps (one entry per valid record)
                cumulative_distances.append(running_distance)
                
                # Altitude
                alt = self._get_field(record, 'enhanced_altitude') or self._get_field(record, 'altitude')
                if alt is not None:
                    altitude_stream.append(alt)
                    altitude_points.append(alt)
                
                # Heart rate
                hr = self._get_field(record, 'heart_rate')
                if hr is not None:
                    hr_stream.append(hr)
                    hr_values.append(hr)
                
                # Cadence
                cadence = self._get_field(record, 'cadence')
                if cadence is not None:
                    cadence_stream.append(cadence)
                    cadence_values.append(cadence)
            
            total_distance = running_distance
            
            # Calculate moving time using common utility
            moving_time = calculate_moving_time(timestamps, cumulative_distances) if len(timestamps) >= 2 else 0
            
            # Calculate max speed using common utility
            max_speed = calculate_max_speed(timestamps, cumulative_distances) if len(timestamps) >= 2 else 0
            
            # Calculate elevation gain using common utility
            total_elevation = calculate_elevation_gain(altitude_points, 5)
            
            # Map FIT fields to our schema
            # Try start_time first, fall back to timestamp if not found
            start_time = self._get_field(session, 'start_time') or self._get_field(session, 'timestamp')
            
            # Convert datetime to ISO format string if needed
            if start_time and hasattr(start_time, 'isoformat'):
                start_time = start_time.isoformat()
            
            # Calculate elapsed time from timestamps
            elapsed_time = 0
            if len(timestamps) >= 2:
                elapsed_time = (timestamps[-1] - timestamps[0]).total_seconds()
            
            # Calculate average speed
            avg_speed = total_distance / moving_time if moving_time > 0 else 0
            
            # Extract sport type for cadence adjustment
            sport = self._get_field(session, 'sport') or ''
            
            # Calculate average cadence
            # FIT stores running cadence in strides/min (one foot), but Strava displays steps/min (both feet)
            # For running/walking/hiking, multiply by 2. For cycling, cadence is already in RPM (correct as-is)
            # Only average non-zero cadence values (exclude stationary periods) to match Strava's calculation
            if cadence_values:
                # Filter out zero cadence values (when stopped)
                moving_cadence = [c for c in cadence_values if c > 0]
                if moving_cadence:
                    avg_cadence = sum(moving_cadence) / len(moving_cadence)
                    if sport.lower() in ['running', 'walking', 'hiking', 'run', 'walk', 'hike']:
                        avg_cadence = avg_cadence * 2
                else:
                    avg_cadence = None
            else:
                avg_cadence = self._get_field(session, 'avg_cadence')
                # Also adjust session-level cadence for running activities
                if avg_cadence and sport.lower() in ['running', 'walking', 'hiking', 'run', 'walk', 'hike']:
                    avg_cadence = avg_cadence * 2
            
            # Extract activity name - check multiple sources
            # Strava FIT files may include name in session or activity messages
            activity_name = None
            
            # Try session message first
            activity_name = self._get_field(session, 'name')
            
            # Try activity message if not found
            if not activity_name:
                for activity_msg in fit_file.get_messages('activity'):
                    activity_name = self._get_field(activity_msg, 'name')
                    if activity_name:
                        break
            
            # Fall back to sport type + date if no name found
            if not activity_name:
                sport = self._get_field(session, 'sport') or 'Activity'
                if start_time and hasattr(start_time, 'strftime'):
                    date_str = start_time.strftime('%b %d, %Y')
                elif start_time and isinstance(start_time, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        date_str = dt.strftime('%b %d, %Y')
                    except:
                        date_str = 'Activity'
                else:
                    date_str = 'Activity'
                activity_name = f"{sport.title()} on {date_str}"
            
            data = {
                "name": activity_name,
                "type": self._map_fit_sport(self._get_field(session, 'sport')),
                "sport_type": self._get_field(session, 'sub_sport'),
                "start_date": start_time,
                "start_date_local": start_time,
                "moving_time": int(moving_time) if moving_time > 0 else self._get_field(session, 'total_timer_time'),
                "elapsed_time": int(elapsed_time) if elapsed_time > 0 else self._get_field(session, 'total_elapsed_time'),
                "distance": total_distance if total_distance > 0 else self._get_field(session, 'total_distance'),
                "total_elevation_gain": total_elevation if total_elevation > 0 else self._get_field(session, 'total_ascent'),
                "average_speed": avg_speed if avg_speed > 0 else (self._get_field(session, 'enhanced_avg_speed') or self._get_field(session, 'avg_speed')),
                "max_speed": max_speed if max_speed > 0 else (self._get_field(session, 'enhanced_max_speed') or self._get_field(session, 'max_speed')),
                "average_heartrate": sum(hr_values) / len(hr_values) if hr_values else self._get_field(session, 'avg_heart_rate'),
                "max_heartrate": max(hr_values) if hr_values else self._get_field(session, 'max_heart_rate'),
                "has_heartrate": len(hr_values) > 0 or self._get_field(session, 'avg_heart_rate') is not None,
                "average_cadence": avg_cadence,
                "average_watts": self._get_field(session, 'avg_power'),
                "max_watts": self._get_field(session, 'max_power'),
                "_hr_stream": hr_stream if hr_stream else None,
                "_latlng_stream": latlng_stream if latlng_stream else None,
                "_altitude_stream": altitude_stream if altitude_stream else None,
            }
            
            # Debug: uncomment to inspect extracted data
            # print(f"DEBUG: final data dict:")
            # print(f"  distance: {data['distance']}")
            # print(f"  moving_time: {data['moving_time']}")
            # print(f"  average_speed: {data['average_speed']}")
            # print(f"  average_heartrate: {data['average_heartrate']}")
            # print(f"  total_elevation_gain: {data['total_elevation_gain']}")
            # print(f"  hr_values count: {len(hr_values)}")
            # print(f"  latlng_stream count: {len(latlng_stream)}")
            # print(f"  altitude_stream count: {len(altitude_stream)}")
            
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
        
        # Collect data from trackpoints
        hr_values = []
        cadence_values = []
        elevation_points = []
        
        # Collect route data for map visualization
        latlng_stream = []
        altitude_stream = []
        hr_stream = []
        timestamps = []
        cumulative_distances = []
        
        for segment in track.segments:
            for i, point in enumerate(segment.points):
                # Collect timestamp
                if point.time is not None:
                    timestamps.append(point.time)
                
                # Collect latlng for route map
                if point.latitude is not None and point.longitude is not None:
                    latlng_stream.append([point.latitude, point.longitude])
                
                # Collect elevation data for smoothing
                if point.elevation is not None:
                    elevation_points.append(point.elevation)
                    altitude_stream.append(point.elevation)
                
                # Calculate cumulative distance
                if i == 0:
                    cumulative_distances.append(0.0)
                else:
                    prev = segment.points[i-1]
                    
                    # Distance: use 2D (horizontal only) to avoid GPS elevation noise
                    distance = point.distance_2d(prev) or 0
                    cumulative_distances.append(cumulative_distances[-1] + distance)
                
                # Extract HR/cadence from extensions (Garmin gpxtpx namespace)
                if point.extensions:
                    hr_val = self._extract_gpx_extension(point, 'hr')
                    cad_val = self._extract_gpx_extension(point, 'cad')
                    
                    if hr_val is not None:
                        hr_values.append(hr_val)
                        hr_stream.append(hr_val)
                    if cad_val is not None:
                        cadence_values.append(cad_val)
        
        # Calculate distance from GPS coordinates using common utility
        total_distance = 0
        if len(latlng_stream) >= 2:
            from utils.activity_calculations import calculate_distance_from_latlng
            total_distance = calculate_distance_from_latlng([tuple(p) for p in latlng_stream])
        
        # Calculate moving time using common utility
        moving_time = calculate_moving_time(timestamps, cumulative_distances) if len(timestamps) >= 2 else 0
        
        # Calculate max speed using common utility
        max_speed = calculate_max_speed(timestamps, cumulative_distances) if len(timestamps) >= 2 else 0
        
        # Calculate elevation gain using common utility
        total_elevation = calculate_elevation_gain(elevation_points, 5)
        
        # Get start/end time
        start_time = None
        for segment in track.segments:
            if segment.points:
                start_time = segment.points[0].time
                break
        
        # Calculate elapsed time from timestamps
        elapsed_time = 0
        if len(timestamps) >= 2:
            elapsed_time = (timestamps[-1] - timestamps[0]).total_seconds()
        
        # Calculate average speed
        avg_speed = total_distance / moving_time if moving_time > 0 else 0
        
        # Calculate average cadence
        # GPX stores running cadence in strides/min (one foot), but Strava displays steps/min (both feet)
        # For running/walking/hiking, multiply by 2. For cycling, cadence is already in RPM (correct as-is)
        # Only average non-zero cadence values (exclude stationary periods) to match Strava's calculation
        avg_cadence = None
        if cadence_values:
            # Filter out zero cadence values (when stopped)
            moving_cadence = [c for c in cadence_values if c > 0]
            if moving_cadence:
                avg_cadence = sum(moving_cadence) / len(moving_cadence)
                # GPX running cadence is per-foot, multiply by 2 for steps/min
                avg_cadence = avg_cadence * 2
        
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
            "average_cadence": avg_cadence,
        }
        
        return self._clean_activity_data(data)
    

    
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
            
            # Extract HR/cadence from trackpoints
            for tp in lap.findall('.//tcx:Trackpoint', namespaces):
                hr = tp.find('.//tcx:HeartRateBpm/tcx:Value', namespaces)
                if hr is not None:
                    hr_values.append(int(hr.text))
                
                cad = tp.find('.//tcx:Cadence', namespaces)
                if cad is not None:
                    cadence_values.append(int(cad.text))
        
        avg_speed = total_distance / total_time if total_time > 0 else 0
        
        # Calculate average cadence
        # TCX stores running cadence in strides/min (one foot), but Strava displays steps/min (both feet)
        # For running/walking/hiking, multiply by 2. For cycling, cadence is already in RPM (correct as-is)
        # Only average non-zero cadence values (exclude stationary periods) to match Strava's calculation
        avg_cadence = None
        if cadence_values:
            # Filter out zero cadence values (when stopped)
            moving_cadence = [c for c in cadence_values if c > 0]
            if moving_cadence:
                avg_cadence = sum(moving_cadence) / len(moving_cadence)
                # TCX running cadence is per-foot, multiply by 2 for steps/min
                if sport.lower() in ['running', 'walking', 'hiking', 'run', 'walk', 'hike']:
                    avg_cadence = avg_cadence * 2
        
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
            "average_cadence": avg_cadence,
        }
        
        return self._clean_activity_data(data)
    
    def _get_field(self, record, field_name: str):
        """Safely extract a field from a FIT record"""
        try:
            # DataMessage has .fields attribute (list of FieldData)
            if hasattr(record, 'fields'):
                for field in record.fields:
                    if field.name == field_name:
                        # Debug: uncomment to trace field extraction
                        # print(f"DEBUG _get_field: {field_name} found, value={field.value}, type={type(field.value)}")
                        return field.value
                # print(f"DEBUG _get_field: {field_name} not found in fields")
                return None
            else:
                # print(f"DEBUG _get_field: record has no 'fields' attribute, type={type(record)}")
                return None
        except Exception as e:
            print(f"DEBUG _get_field: {field_name} exception: {type(e).__name__}: {e}")
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
        # Debug: uncomment to trace data cleaning
        # print(f"DEBUG _clean_activity_data input: {data}")
        
        # Remove None values
        cleaned = {k: v for k, v in data.items() if v is not None}
        
        # Debug: uncomment to trace data cleaning
        # print(f"DEBUG _clean_activity_data after None removal: {cleaned}")
        
        # Ensure required fields
        if 'name' not in cleaned:
            cleaned['name'] = 'Activity'
        if 'type' not in cleaned:
            cleaned['type'] = 'Other'
        if 'start_date' not in cleaned:
            # Debug: uncomment to trace missing start_date
            # print(f"DEBUG: start_date missing from cleaned data!")
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
