"""
Tests for API routers (activities, uploads, auth, trends)
"""
import pytest
from datetime import datetime


class TestActivitiesRouter:
    """Test /activities endpoints"""
    
    def test_list_activities_empty(self, client, sample_user):
        """Test listing activities when none exist"""
        response = client.get(
            "/activities/",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["activities"] == []
        assert data["pagination"]["total"] == 0
    
    def test_list_activities_with_data(self, client, sample_activity):
        """Test listing activities with data"""
        response = client.get(
            "/activities/",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 1
        assert data["activities"][0]["name"] == "Morning Run"
        assert data["activities"][0]["distance"] == 5000.0
    
    def test_list_activities_filter_by_type(self, client, sample_activity):
        """Test filtering activities by type"""
        response = client.get(
            "/activities/?type=Run",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 1
        
        response = client.get(
            "/activities/?type=Ride",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        data = response.json()
        assert len(data["activities"]) == 0
    
    def test_list_activities_pagination(self, client, db_session, sample_user):
        """Test pagination of activities"""
        from models.activity import Activity
        
        # Create 10 activities
        for i in range(10):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, i+1, 8, 0, 0),
                start_date_local=datetime(2024, 1, i+1, 8, 0, 0),
                moving_time=1800,
                distance=5000.0
            )
            db_session.add(activity)
        db_session.commit()
        
        response = client.get(
            "/activities/?per_page=5&page=1",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 5
        assert data["pagination"]["total"] == 10
        assert data["pagination"]["total_pages"] == 2
    
    def test_get_activity_detail(self, client, sample_activity):
        """Test getting activity detail"""
        response = client.get(
            f"/activities/{sample_activity.id}",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Morning Run"
        assert data["distance"] == 5000.0
        assert data["average_heartrate"] == 150.0
    
    def test_get_activity_not_found(self, client, sample_user):
        """Test getting non-existent activity"""
        response = client.get(
            "/activities/99999",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 404



    def test_delete_activity(self, client, sample_activity):
        """Test deleting an activity"""
        response = client.delete(
            f"/activities/{sample_activity.id}",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Activity deleted successfully"
        
        # Verify it's gone
        response = client.get(
            f"/activities/{sample_activity.id}",
            headers={"Authorization": f"Bearer session_{sample_activity.user_id}_1234567890"}
        )
        assert response.status_code == 404
    
    def test_delete_activity_not_found(self, client, sample_user):
        """Test deleting non-existent activity"""
        response = client.delete(
            "/activities/99999",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 404


class TestUploadsRouter:
    """Test /uploads endpoints"""
    
    def test_upload_unsupported_format(self, client, sample_user):
        """Test uploading unsupported file format"""
        response = client.post(
            "/uploads/",
            files={"file": ("test.csv", b"fake content", "text/csv")},
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    
    def test_upload_file_too_large(self, client, sample_user):
        """Test uploading file larger than 50MB"""
        # Create a fake 60MB file
        large_content = b"x" * (60 * 1024 * 1024)
        response = client.post(
            "/uploads/",
            files={"file": ("large.fit", large_content, "application/octet-stream")},
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()


class TestAuthRouter:
    """Test /auth endpoints"""
    
    def test_strava_callback_creates_user(self, client, db_session, mock_strava_api, mocker):
        """Test Strava OAuth callback creates new user"""
        from unittest.mock import AsyncMock, MagicMock
        
        # Create mock response objects
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_at": 9999999999
        }
        
        athlete_response = MagicMock()
        athlete_response.status_code = 200
        athlete_response.json.return_value = mock_strava_api["athlete"]
        
        # Mock the AsyncClient context manager
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=token_response)
        mock_client.get = AsyncMock(return_value=athlete_response)
        
        mocker.patch("httpx.AsyncClient", return_value=mock_client)
        
        response = client.post("/auth/strava/callback?code=test_code")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["strava_athlete_id"] == 123456789
    
    def test_strava_callback_updates_existing_user(self, client, db_session, sample_user, mock_strava_api, mocker):
        """Test Strava OAuth callback updates existing user"""
        from unittest.mock import AsyncMock, MagicMock
        
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "updated_access_token",
            "refresh_token": "updated_refresh_token",
            "expires_at": 9999999999
        }
        
        athlete_response = MagicMock()
        athlete_response.status_code = 200
        athlete_response.json.return_value = mock_strava_api["athlete"]
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=token_response)
        mock_client.get = AsyncMock(return_value=athlete_response)
        
        mocker.patch("httpx.AsyncClient", return_value=mock_client)
        
        response = client.post("/auth/strava/callback?code=test_code")
        assert response.status_code == 200
        
        # Verify user was updated
        from models.user import User
        user = db_session.query(User).filter(User.strava_athlete_id == 123456789).first()
        assert user.access_token == "updated_access_token"


class TestTrendsRouter:
    """Test /trends endpoints"""
    
    def test_get_metric_trend_stub(self, client, sample_user):
        """Test metric trend endpoint (currently stubbed)"""
        response = client.get(
            "/trends/metrics?metric_type=average_speed",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metric_type"] == "average_speed"
        assert data["data_points"] == []
    
    def test_get_percentile_bands_stub(self, client, sample_user):
        """Test percentile bands endpoint (currently stubbed)"""
        response = client.get(
            "/trends/percentiles?metric_type=average_speed&activity_type=Run",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metric_type"] == "average_speed"
        assert data["bands"] == []

    def test_get_activity_detail_includes_has_streams(self, client, db_session, sample_user):
        """Test that activity detail response includes has_streams field"""
        from models.activity import Activity
        from datetime import datetime
        
        activity = Activity(
            user_id=sample_user.id,
            strava_id=99999,
            name="Test Activity",
            type="Run",
            start_date=datetime.utcnow(),
            start_date_local=datetime.utcnow(),
            distance=5000.0,
            moving_time=1800,
            has_streams=True,
        )
        db_session.add(activity)
        db_session.commit()
        
        response = client.get(
            f"/activities/{activity.id}",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_streams" in data
        assert data["has_streams"] is True

    def test_get_activity_streams(self, client, db_session, sample_user):
        """Test getting activity streams endpoint"""
        from models.activity import Activity
        from models.activity_stream import ActivityStream
        from datetime import datetime
        
        activity = Activity(
            user_id=sample_user.id,
            strava_id=88888,
            name="Stream Test",
            type="Run",
            start_date=datetime.utcnow(),
            start_date_local=datetime.utcnow(),
            has_streams=True,
        )
        db_session.add(activity)
        db_session.flush()
        
        stream = ActivityStream(
            user_id=sample_user.id,
            activity_id=activity.id,
            stream_type="latlng",
            data=[[40.7128, -74.0060], [40.7129, -74.0061]],
        )
        db_session.add(stream)
        db_session.commit()
        
        response = client.get(
            f"/activities/{activity.id}/streams",
            headers={"Authorization": f"Bearer session_{sample_user.id}_1234567890"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "streams" in data
        assert "latlng" in data["streams"]
        assert len(data["streams"]["latlng"]["data"]) == 2
