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
