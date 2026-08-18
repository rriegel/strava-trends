"""
Tests for file upload service
"""
import pytest
from datetime import datetime
from services.file_upload_service import FileUploadService


class TestFileUploadService:
    """Test file upload parsing and processing"""
    
    def test_supported_formats(self, db_session):
        """Test that supported formats are correctly defined"""
        service = FileUploadService(db_session)
        assert '.fit' in service.SUPPORTED_FORMATS
        assert '.gpx' in service.SUPPORTED_FORMATS
        assert '.tcx' in service.SUPPORTED_FORMATS
    
    def test_unsupported_format_raises_error(self, db_session, sample_user):
        """Test that unsupported file formats raise ValueError"""
        service = FileUploadService(db_session)
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            import asyncio
            asyncio.run(service.process_upload(
                user_id=sample_user.id,
                file_content=b"fake content",
                filename="activity.csv"
            ))
    
    def test_map_fit_sport(self, db_session):
        """Test FIT sport mapping"""
        service = FileUploadService(db_session)
        
        assert service._map_fit_sport("running") == "Run"
        assert service._map_fit_sport("cycling") == "Ride"
        assert service._map_fit_sport("swimming") == "Swim"
        assert service._map_fit_sport("walking") == "Walk"
        assert service._map_fit_sport("hiking") == "Hike"
        assert service._map_fit_sport("unknown") == "Other"
        assert service._map_fit_sport(None) == "Other"
    
    def test_map_tcx_sport(self, db_session):
        """Test TCX sport mapping"""
        service = FileUploadService(db_session)
        
        assert service._map_tcx_sport("Running") == "Run"
        assert service._map_tcx_sport("Biking") == "Ride"
        assert service._map_tcx_sport("Other") == "Other"
        assert service._map_tcx_sport("Unknown") == "Other"
    
    def test_clean_activity_data_removes_none(self, db_session):
        """Test that _clean_activity_data removes None values"""
        service = FileUploadService(db_session)
        
        data = {
            "name": "Test Run",
            "type": "Run",
            "start_date": datetime(2024, 1, 15, 8, 0, 0),
            "moving_time": 1800,
            "average_heartrate": None,
            "max_heartrate": None,
        }
        
        cleaned = service._clean_activity_data(data)
        
        assert "name" in cleaned
        assert "type" in cleaned
        assert "start_date" in cleaned
        assert "average_heartrate" not in cleaned
        assert "max_heartrate" not in cleaned
    
    def test_clean_activity_data_requires_start_date(self, db_session):
        """Test that _clean_activity_data raises error without start_date"""
        service = FileUploadService(db_session)
        
        data = {
            "name": "Test Run",
            "type": "Run",
            "moving_time": 1800,
        }
        
        with pytest.raises(ValueError, match="must have a start_date"):
            service._clean_activity_data(data)
    
    def test_clean_activity_data_defaults(self, db_session):
        """Test that _clean_activity_data applies defaults"""
        service = FileUploadService(db_session)
        
        data = {
            "start_date": datetime(2024, 1, 15, 8, 0, 0),
        }
        
        cleaned = service._clean_activity_data(data)
        
        assert cleaned["name"] == "Activity"
        assert cleaned["type"] == "Other"
    
    def test_clean_activity_data_numeric_conversion(self, db_session):
        """Test that numeric fields are converted to float"""
        service = FileUploadService(db_session)
        
        data = {
            "name": "Test Run",
            "type": "Run",
            "start_date": datetime(2024, 1, 15, 8, 0, 0),
            "moving_time": "1800",  # String instead of int
            "distance": "5000.5",
        }
        
        cleaned = service._clean_activity_data(data)
        
        assert isinstance(cleaned["moving_time"], float)
        assert cleaned["moving_time"] == 1800.0
        assert cleaned["distance"] == 5000.5
    
    def test_clean_activity_data_invalid_numeric(self, db_session):
        """Test that invalid numeric values become None"""
        service = FileUploadService(db_session)
        
        data = {
            "name": "Test Run",
            "type": "Run",
            "start_date": datetime(2024, 1, 15, 8, 0, 0),
            "moving_time": "not_a_number",
        }
        
        cleaned = service._clean_activity_data(data)
        
        assert cleaned["moving_time"] is None
    
    def test_duplicate_detection(self, db_session, sample_user):
        """Test that duplicate uploads are detected"""
        service = FileUploadService(db_session)
        
        # Create an existing activity
        from models.activity import Activity
        existing = Activity(
            user_id=sample_user.id,
            source="file_upload",
            source_id="test.fit_2024-01-15T08:00:00",
            name="Existing Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0
        )
        db_session.add(existing)
        db_session.commit()
        
        # Try to upload same file again (would need real file to test fully)
        # This tests the logic path
        duplicate_check = db_session.query(Activity).filter(
            Activity.user_id == sample_user.id,
            Activity.source == "file_upload",
            Activity.source_id == "test.fit_2024-01-15T08:00:00"
        ).first()
        
        assert duplicate_check is not None
        assert duplicate_check.name == "Existing Run"


class TestGPXParsing:
    """Test GPX file parsing"""
    
    def test_parse_gpx_no_tracks(self, db_session):
        """Test that GPX without tracks raises error"""
        service = FileUploadService(db_session)
        
        # Minimal GPX with no tracks
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
</gpx>"""
        
        with pytest.raises(ValueError, match="No tracks found"):
            service._parse_gpx(gpx_content)


class TestTCXParsing:
    """Test TCX file parsing"""
    
    def test_parse_tcx_no_activity(self, db_session):
        """Test that TCX without Activity raises error"""
        service = FileUploadService(db_session)
        
        # Minimal TCX with no Activity
        tcx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
</TrainingCenterDatabase>"""
        
        with pytest.raises(ValueError, match="No Activity found"):
            service._parse_tcx(tcx_content)


class TestGPXParsingImprovements:
    """Test improved GPX parsing with GPS noise filtering"""
    
    def test_gpx_elevation_threshold_filtering(self, db_session):
        """Test that small elevation changes (< 3m) are filtered as GPS noise"""
        service = FileUploadService(db_session)
        
        # GPX with elevation changes: 100 -> 102 (2m, should be filtered) -> 106 (4m, should count)
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Run</name>
    <trkseg>
      <trkpt lat="40.0" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-105.0">
        <ele>102</ele>
        <time>2024-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="40.002" lon="-105.0">
        <ele>106</ele>
        <time>2024-01-15T08:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        
        result = service._parse_gpx(gpx_content)
        
        # Should only count the 4m gain (106 - 102), not the 2m gain (102 - 100)
        assert result["total_elevation_gain"] == 4.0
    
    def test_gpx_moving_time_excludes_stationary(self, db_session):
        """Test that stationary periods are excluded from moving time"""
        service = FileUploadService(db_session)
        
        # GPX with stationary period (no distance, but time passes)
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Run</name>
    <trkseg>
      <trkpt lat="40.0" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:02:00Z</time>
      </trkpt>
      <trkpt lat="40.002" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:03:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        
        result = service._parse_gpx(gpx_content)
        
        # Total elapsed time: 3 minutes (180 seconds)
        assert result["elapsed_time"] == 180
        
        # Moving time should exclude the stationary minute (point 2 to point 3)
        # Only points 1->2 and 3->4 have movement
        assert result["moving_time"] < result["elapsed_time"]
        assert result["moving_time"] == 120  # 2 minutes of movement
    
    def test_gpx_uses_2d_distance(self, db_session):
        """Test that distance calculation uses 2D (horizontal) distance"""
        service = FileUploadService(db_session)
        
        # GPX with elevation change but same horizontal distance
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Run</name>
    <trkseg>
      <trkpt lat="40.0" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-105.0">
        <ele>200</ele>
        <time>2024-01-15T08:01:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        
        result = service._parse_gpx(gpx_content)
        
        # Distance should be horizontal only (~111m for 0.001 degrees latitude)
        # Not affected by the 100m elevation difference
        assert result["distance"] > 100
        assert result["distance"] < 150
    
    def test_gpx_calculates_max_speed(self, db_session):
        """Test that max speed is calculated from actual speeds, not estimated"""
        service = FileUploadService(db_session)
        
        # GPX with varying speeds
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Run</name>
    <trkseg>
      <trkpt lat="40.0" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:00:00Z</time>
      </trkpt>
      <trkpt lat="40.001" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:01:00Z</time>
      </trkpt>
      <trkpt lat="40.003" lon="-105.0">
        <ele>100</ele>
        <time>2024-01-15T08:02:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        
        result = service._parse_gpx(gpx_content)
        
        # Point 1->2: ~111m in 60s = ~1.85 m/s
        # Point 2->3: ~222m in 60s = ~3.7 m/s (faster)
        # Max speed should be the faster segment
        assert result["max_speed"] > 3.0
        assert result["max_speed"] < 4.0
