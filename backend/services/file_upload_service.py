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
        
        # Create new activity
        activity = Activity(
            user_id=user_id,
            source="file_upload",
            source_id=source_id,
            **activity_data
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        return {
            "status": "success",
            "activity_id": activity.id,
            "activity_name": activity.name,
            "activity_type": activity.type,
            "start_date": activity.start_date.isoformat() if activity.start_date else None
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
            
            # Map FIT fields to our schema
            data = {
                "name": self._get_field(session, 'event') or "FIT Activity",
                "type": self._map_fit_sport(self._get_field(session, 'sport')),
                "sport_type": self._get_field(session, 'sub_sport'),
                "start_date": self._get_field(session, 'start_time'),
                "start_date_local": self._get_field(session, 'start_time'),
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
        
        # Calculate summary stats
        total_distance = 0
        total_elevation = 0
        total_time = 0
        hr_values = []
        cadence_values = []
        
        for segment in track.segments:
            for i, point in enumerate(segment.points):
                if i > 0 and segment.points[i-1]:
                    prev = segment.points[i-1]
                    total_distance += point.distance_3d(prev) or point.distance_2d(prev) or 0
                    if point.elevation and prev.elevation and point.elevation > prev.elevation:
                        total_elevation += point.elevation - prev.elevation
                    if point.time and prev.time:
                        total_time += (point.time - prev.time).total_seconds()
                
                # Extract HR/cadence from extensions if present
                if point.extensions:
                    # GPX extensions vary by device; this is a simplified extraction
                    pass
        
        # Get start/end time
        start_time = None
        for segment in track.segments:
            if segment.points:
                start_time = segment.points[0].time
                break
        
        avg_speed = total_distance / total_time if total_time > 0 else 0
        
        data = {
            "name": track.name or "GPX Activity",
            "type": "Run",  # GPX doesn't always specify sport; default to Run
            "sport_type": None,
            "start_date": start_time,
            "start_date_local": start_time,
            "moving_time": int(total_time),
            "elapsed_time": int(total_time),
            "distance": total_distance,
            "total_elevation_gain": total_elevation,
            "average_speed": avg_speed,
            "max_speed": avg_speed * 1.2,  # Estimate
            "average_heartrate": sum(hr_values) / len(hr_values) if hr_values else None,
            "max_heartrate": max(hr_values) if hr_values else None,
            "has_heartrate": len(hr_values) > 0,
            "average_cadence": sum(cadence_values) / len(cadence_values) if cadence_values else None,
        }
        
        return self._clean_activity_data(data)
    
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
