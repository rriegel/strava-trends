"""
Tests for Activity model
"""
import pytest
from datetime import datetime
from models.activity import Activity


class TestActivityModel:
    """Test Activity model creation and validation"""
    
    def test_create_activity(self, db_session, sample_user):
        """Test creating a basic activity"""
        activity = Activity(
            user_id=sample_user.id,
            source="strava",
            source_id="strava_99999",
            name="Test Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.id is not None
        assert activity.name == "Test Run"
        assert activity.source == "strava"
        assert activity.source_id == "strava_99999"
        assert activity.distance == 5000.0
    
    def test_activity_source_agnostic(self, db_session, sample_user):
        """Test that activities can come from different sources"""
        strava_activity = Activity(
            user_id=sample_user.id,
            source="strava",
            source_id="strava_111",
            name="Strava Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0
        )
        
        file_activity = Activity(
            user_id=sample_user.id,
            source="file_upload",
            source_id="fit_file_20240115.fit",
            name="FIT File Run",
            type="Run",
            start_date=datetime(2024, 1, 16, 8, 0, 0),
            start_date_local=datetime(2024, 1, 16, 8, 0, 0),
            moving_time=1900,
            distance=5200.0
        )
        
        db_session.add_all([strava_activity, file_activity])
        db_session.commit()
        
        assert strava_activity.source == "strava"
        assert file_activity.source == "file_upload"
    
    def test_activity_with_heart_rate(self, db_session, sample_user):
        """Test activity with heart rate data"""
        activity = Activity(
            user_id=sample_user.id,
            source="strava",
            source_id="strava_hr_test",
            name="HR Test Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0,
            average_heartrate=150.0,
            max_heartrate=175.0,
            has_heartrate=True
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.has_heartrate is True
        assert activity.average_heartrate == 150.0
        assert activity.max_heartrate == 175.0
    
    def test_activity_without_heart_rate(self, db_session, sample_user):
        """Test activity without heart rate data"""
        activity = Activity(
            user_id=sample_user.id,
            source="file_upload",
            source_id="no_hr.fit",
            name="No HR Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0,
            has_heartrate=False
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.has_heartrate is False
        assert activity.average_heartrate is None
    
    def test_activity_distance_bucket(self, db_session, sample_user):
        """Test activity distance bucketing"""
        activity = Activity(
            user_id=sample_user.id,
            source="strava",
            source_id="strava_bucket_test",
            name="5K Run",
            type="Run",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=1800,
            distance=5000.0,
            distance_bucket="5k"
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.distance_bucket == "5k"
    
    def test_activity_with_power_data(self, db_session, sample_user):
        """Test activity with power meter data"""
        activity = Activity(
            user_id=sample_user.id,
            source="strava",
            source_id="strava_power_test",
            name="Power Ride",
            type="Ride",
            start_date=datetime(2024, 1, 15, 8, 0, 0),
            start_date_local=datetime(2024, 1, 15, 8, 0, 0),
            moving_time=3600,
            distance=30000.0,
            average_watts=200.0,
            weighted_average_watts=210.0,
            max_watts=800.0,
            kilojoules=720.0
        )
        db_session.add(activity)
        db_session.commit()
        
        assert activity.average_watts == 200.0
        assert activity.weighted_average_watts == 210.0
        assert activity.max_watts == 800.0
        assert activity.kilojoules == 720.0
