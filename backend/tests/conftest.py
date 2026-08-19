"""
Pytest configuration and fixtures for Strava Trends backend tests.
"""
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from database import Base, get_db
from main import app
from models.user import User
from models.activity import Activity


# Use PostgreSQL test database
SQLALCHEMY_DATABASE_URL = "postgresql://test_user:test_password@localhost:5432/strava_trends_test"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    # Clear connection pool to avoid stale connections after table drops
    engine.dispose()
    
    # Drop tables in reverse dependency order to handle circular dependencies
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS effort_groups CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS route_clusters CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS routes CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS activity_streams CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS activities CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS computed_metrics CASCADE"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS effort_groups CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS route_clusters CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS routes CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS activity_streams CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS activities CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS computed_metrics CASCADE"))
            conn.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db_session):
    """Async HTTP client for testing async endpoints"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing"""
    user = User(
        strava_athlete_id=123456789,
        username="testuser",
        firstname="Test",
        lastname="User",
        email="test@example.com",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expires_at=datetime.now() + timedelta(days=1)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_activity(db_session, sample_user):
    """Create a sample activity for testing"""
    activity = Activity(
        user_id=sample_user.id,
        source="strava",
        source_id="strava_12345",
        name="Morning Run",
        type="Run",
        sport_type="Run",
        start_date=datetime(2024, 1, 15, 8, 0, 0),
        start_date_local=datetime(2024, 1, 15, 8, 0, 0),
        moving_time=1800,
        elapsed_time=1850,
        distance=5000.0,
        total_elevation_gain=50.0,
        average_speed=2.78,
        max_speed=3.5,
        average_heartrate=150.0,
        max_heartrate=175.0,
        has_heartrate=True,
        average_cadence=85.0,
        device_name="Forerunner 945",
        distance_bucket="5k",
        effort_zone="tempo"
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity


@pytest.fixture
def mock_strava_api():
    """Mock Strava API responses"""
    return {
        "athlete": {
            "id": 123456789,
            "firstname": "Test",
            "lastname": "User",
            "profile": "https://example.com/profile.jpg"
        },
        "activities": [
            {
                "id": 12345,
                "name": "Morning Run",
                "type": "Run",
                "sport_type": "Run",
                "start_date": "2024-01-15T08:00:00Z",
                "start_date_local": "2024-01-15T08:00:00Z",
                "moving_time": 1800,
                "elapsed_time": 1850,
                "distance": 5000.0,
                "total_elevation_gain": 50.0,
                "average_speed": 2.78,
                "max_speed": 3.5,
                "average_heartrate": 150.0,
                "max_heartrate": 175.0,
                "average_cadence": 85.0,
                "device_name": "Forerunner 945"
            }
        ]
    }


# Configure pytest-asyncio
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as async")
