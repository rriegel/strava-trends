"""
Integration tests for trends endpoint
"""
import pytest
from datetime import datetime, timedelta
from models.activity import Activity
from models.computed_metric import ComputedMetric


class TestTrendsEndpoint:
    """Test /trends/metrics endpoint"""
    
    def test_get_metric_trend_no_data(self, client, sample_user):
        """Test trend endpoint with no activities"""
        response = client.get("/trends/metrics?metric_type=average_speed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["metric_type"] == "average_speed"
        assert data["data_points"] == []
        assert data["aggregated_data"] == []
        assert data["trend"]["slope"] == 0
        assert data["trend"]["direction"] == "stable"
    
    def test_get_metric_trend_with_activities(self, client, db_session, sample_user):
        """Test trend endpoint with activity data"""
        # Create 5 activities with increasing speed over time
        for i in range(5):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=1800,
                distance=5000.0,
                average_speed=2.5 + i * 0.1,  # Increasing speed
                average_heartrate=150.0 - i * 2,  # Decreasing HR
                has_heartrate=True,
                distance_bucket="5K"
            )
            db_session.add(activity)
        
        db_session.commit()
        
        response = client.get("/trends/metrics?metric_type=average_speed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["metric_type"] == "average_speed"
        assert len(data["data_points"]) == 5
        assert data["trend"]["direction"] == "increasing"
        assert data["trend"]["slope"] > 0
        assert data["trend"]["r_squared"] > 0.8
    
    def test_get_metric_trend_with_filters(self, client, db_session, sample_user):
        """Test trend endpoint with activity type filter"""
        # Create runs and rides
        for i in range(3):
            run = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"run_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=1800,
                distance=5000.0,
                average_speed=3.0
            )
            db_session.add(run)
            
            ride = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"ride_{i}",
                name=f"Ride {i}",
                type="Ride",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=3600,
                distance=20000.0,
                average_speed=5.5
            )
            db_session.add(ride)
        
        db_session.commit()
        
        # Filter by Run type
        response = client.get("/trends/metrics?metric_type=average_speed&activity_type=Run")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data_points"]) == 3
        # All runs have speed 3.0
        for point in data["data_points"]:
            assert point["value"] == 3.0
    
    def test_get_metric_trend_with_date_range(self, client, db_session, sample_user):
        """Test trend endpoint with date range filter"""
        # Create activities spanning 3 months
        for i in range(9):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*14),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*14),
                moving_time=1800,
                distance=5000.0,
                average_speed=3.0
            )
            db_session.add(activity)
        
        db_session.commit()
        
        # Filter to February only
        response = client.get(
            "/trends/metrics?metric_type=average_speed"
            "&start_date=2024-02-01T00:00:00"
            "&end_date=2024-02-29T23:59:59"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include activities in February
        assert len(data["data_points"]) > 0
        for point in data["data_points"]:
            date = datetime.fromisoformat(point["date"])
            assert date.month == 2
    
    def test_get_metric_trend_with_distance_bucket(self, client, db_session, sample_user):
        """Test trend endpoint with distance bucket filter"""
        # Create 5K and 10K activities
        for i in range(3):
            activity_5k = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"5k_{i}",
                name=f"5K {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=1500,
                distance=5000.0,
                average_speed=3.3,
                distance_bucket="5K"
            )
            db_session.add(activity_5k)
            
            activity_10k = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"10k_{i}",
                name=f"10K {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=3300,
                distance=10000.0,
                average_speed=3.0,
                distance_bucket="10K"
            )
            db_session.add(activity_10k)
        
        db_session.commit()
        
        # Filter by 5K bucket
        response = client.get("/trends/metrics?metric_type=average_speed&distance_bucket=5K")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data_points"]) == 3
        for point in data["data_points"]:
            assert point["value"] == 3.3
    
    def test_get_metric_trend_with_aggregation(self, client, db_session, sample_user):
        """Test trend endpoint with weekly aggregation"""
        # Create multiple activities per week
        for week in range(3):
            for day in range(3):
                activity = Activity(
                    user_id=sample_user.id,
                    source="strava",
                    source_id=f"strava_{week}_{day}",
                    name=f"Run {week}-{day}",
                    type="Run",
                    start_date=datetime(2024, 1, 1) + timedelta(weeks=week, days=day*2),
                    start_date_local=datetime(2024, 1, 1) + timedelta(weeks=week, days=day*2),
                    moving_time=1800,
                    distance=5000.0,
                    average_speed=3.0 + day * 0.1
                )
                db_session.add(activity)
        
        db_session.commit()
        
        response = client.get("/trends/metrics?metric_type=average_speed&aggregation=weekly")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have aggregated data
        assert len(data["aggregated_data"]) > 0
        # Each aggregated period should have count, min, max, mean
        for period in data["aggregated_data"]:
            assert "period" in period
            assert "value" in period
            assert "min" in period
            assert "max" in period
            assert "count" in period
    
    def test_get_metric_trend_computed_metric(self, client, db_session, sample_user):
        """Test trend for computed metrics like hr_pace_ratio"""
        # Create activities
        for i in range(5):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=1800,
                distance=5000.0,
                average_speed=3.0,
                average_heartrate=150.0 - i * 5,  # Decreasing HR
                has_heartrate=True
            )
            db_session.add(activity)
            db_session.flush()
            
            # Create computed metric (hr_pace_ratio)
            metric = ComputedMetric(
                user_id=sample_user.id,
                activity_id=activity.id,
                metric_type="hr_pace_ratio",
                value=150.0 / 3.0 - i * 1.5  # Decreasing ratio
            )
            db_session.add(metric)
        
        db_session.commit()
        
        response = client.get("/trends/metrics?metric_type=hr_pace_ratio")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["data_points"]) == 5
        assert data["trend"]["direction"] == "decreasing"
        assert data["trend"]["slope"] < 0


class TestMultiMetricTrend:
    """Test /trends/metrics/multi endpoint"""
    
    def test_get_multi_metric_trend(self, client, db_session, sample_user):
        """Test multi-metric trend endpoint"""
        # Create activities
        for i in range(5):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*7),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*7),
                moving_time=1800,
                distance=5000.0,
                average_speed=2.5 + i * 0.1,
                average_heartrate=150.0 - i * 2,
                has_heartrate=True
            )
            db_session.add(activity)
        
        db_session.commit()
        
        response = client.get("/trends/metrics/multi?metric_types=average_speed,average_heartrate")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert "average_speed" in data["metrics"]
        assert "average_heartrate" in data["metrics"]
        
        assert len(data["metrics"]["average_speed"]["data_points"]) == 5
        assert len(data["metrics"]["average_heartrate"]["data_points"]) == 5


class TestPercentileBands:
    """Test /trends/percentiles endpoint"""
    
    def test_get_percentile_bands(self, client, db_session, sample_user):
        """Test percentile bands endpoint"""
        # Create activities with varying speeds
        for i in range(20):
            activity = Activity(
                user_id=sample_user.id,
                source="strava",
                source_id=f"strava_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2024, 1, 1) + timedelta(days=i*3),
                start_date_local=datetime(2024, 1, 1) + timedelta(days=i*3),
                moving_time=1800,
                distance=5000.0,
                average_speed=2.5 + (i % 5) * 0.2,  # Varying speeds
                distance_bucket="5K"
            )
            db_session.add(activity)
        
        db_session.commit()
        
        response = client.get(
            "/trends/percentiles?metric_type=average_speed"
            "&activity_type=Run"
            "&percentiles=10,50,90"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["metric_type"] == "average_speed"
        assert data["activity_type"] == "Run"
        assert len(data["bands"]) > 0
        
        # Each band should have percentile values
        for band in data["bands"]:
            assert "date" in band
            assert "p10" in band
            assert "p50" in band
            assert "p90" in band
            assert band["p10"] <= band["p50"] <= band["p90"]
