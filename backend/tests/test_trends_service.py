"""
Tests for AnalyticsEngine conversion helpers and TrendsService.

Covers the pace display-unit contract:
- speed_to_pace conversion math
- display-unit conversion applied server-side (average_speed -> min/km)
- trend direction/R² computed on converted (pace) values
- unit labels returned in responses
"""
from datetime import datetime, timedelta

import pytest

from services.analytics_engine import AnalyticsEngine
from services.trends_service import TrendsService


@pytest.fixture
def trends_service(db_session):
    return TrendsService(db_session)


def _make_activity(db_session, user_id, idx, average_speed=None, **overrides):
    from models.activity import Activity
    defaults = dict(
        user_id=user_id,
        source="strava",
        source_id=f"strava_trend_{idx}",
        name=f"Run {idx}",
        type="Run",
        sport_type="Run",
        start_date=datetime(2024, 1, 1) + timedelta(days=7 * idx),
        start_date_local=datetime(2024, 1, 1) + timedelta(days=7 * idx),
        moving_time=1800,
        distance=5000.0,
    )
    defaults.update(overrides)
    if average_speed is not None:
        defaults["average_speed"] = average_speed
    activity = Activity(**defaults)
    db_session.add(activity)
    return activity


class TestSpeedToPace:
    """speed_to_pace conversion math"""

    def test_known_conversions(self):
        # 3.3333 m/s -> 5:00 min/km = 5.0 decimal minutes
        assert abs(AnalyticsEngine.speed_to_pace(3.3333) - 5.0004) < 0.001
        # 2.5 m/s -> 6:40 min/km = 6.6667 decimal minutes
        assert abs(AnalyticsEngine.speed_to_pace(2.5) - 6.6667) < 0.001
        # 5.0 m/s -> 3:20 min/km = 3.3333 decimal minutes
        assert abs(AnalyticsEngine.speed_to_pace(5.0) - 3.3333) < 0.001

    def test_invalid_speeds_return_zero(self):
        assert AnalyticsEngine.speed_to_pace(0) == 0.0
        assert AnalyticsEngine.speed_to_pace(-1.0) == 0.0
        # Defensive: runtime must not crash on None even though type hints say float
        assert AnalyticsEngine.speed_to_pace(None) == 0.0  # type: ignore[arg-type]

    def test_conversion_is_reciprocal(self):
        # Doubling speed halves pace
        fast = AnalyticsEngine.speed_to_pace(4.0)
        slow = AnalyticsEngine.speed_to_pace(2.0)
        assert abs(fast * 2 - slow) < 1e-9


class TestTrendOnDisplayUnits:
    """Trend statistics run on converted (display) values"""

    def _dates(self, n):
        return [datetime(2024, 1, 1) + timedelta(days=7 * i) for i in range(n)]

    def test_improving_speed_gives_decreasing_pace(self):
        # Speeds increasing 2.5 -> 2.85 m/s = pace improving (decreasing)
        speeds = [2.5 + 0.05 * i for i in range(8)]
        paces = [AnalyticsEngine.speed_to_pace(s) for s in speeds]
        trend = AnalyticsEngine.calculate_trend(self._dates(8), paces, metric_type="average_speed")
        assert trend["direction"] == "decreasing"
        assert trend["r_squared"] > 0.99

    def test_r_squared_differs_from_raw_speed_fit(self):
        # The whole point of the fix: R² on pace != R² on speed
        speeds = [2.5 + 0.05 * i for i in range(8)]
        paces = [AnalyticsEngine.speed_to_pace(s) for s in speeds]
        on_pace = AnalyticsEngine.calculate_trend(self._dates(8), paces)
        on_speed = AnalyticsEngine.calculate_trend(self._dates(8), speeds)
        # Both fit well here (values are near-linear), but slopes differ in sign
        assert on_pace["slope"] < 0 < on_speed["slope"]

    def test_pace_threshold_is_tighter_than_default(self):
        assert AnalyticsEngine.direction_threshold("average_speed") == 0.005
        assert AnalyticsEngine.direction_threshold("grade_adjusted_pace") == 0.005
        assert AnalyticsEngine.direction_threshold("average_heartrate") == 0.1
        assert AnalyticsEngine.direction_threshold("unknown_metric") == 0.01

    def test_insufficient_data(self):
        trend = AnalyticsEngine.calculate_trend([datetime(2024, 1, 1)], [1.0])
        assert trend == {"slope": 0, "direction": "stable", "r_squared": 0}


class TestMetricTrendService:
    """TrendsService.get_metric_trend returns display-unit values"""

    def test_average_speed_returned_as_pace(self, db_session, sample_user, trends_service):
        # 2.78 m/s = 5:59.7 min/km ~ 5.995 decimal minutes
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        _make_activity(db_session, sample_user.id, 1, average_speed=2.78)
        db_session.commit()

        result = trends_service.get_metric_trend(user_id=sample_user.id, metric_type="average_speed")

        assert result["unit"] == "min/km"
        assert len(result["data_points"]) == 2
        expected = AnalyticsEngine.speed_to_pace(2.78)
        for point in result["data_points"]:
            assert abs(point["value"] - expected) < 0.001
        # Aggregated values are also converted
        for agg in result["aggregated_data"]:
            assert abs(agg["value"] - expected) < 0.001

    def test_non_pace_metric_passthrough(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78, average_heartrate=150.0)
        _make_activity(db_session, sample_user.id, 1, average_speed=2.78, average_heartrate=152.0)
        db_session.commit()

        result = trends_service.get_metric_trend(user_id=sample_user.id, metric_type="average_heartrate")

        assert result["unit"] == "bpm"
        values = [p["value"] for p in result["data_points"]]
        assert values == [150.0, 152.0]

    def test_trend_direction_computed_on_pace(self, db_session, sample_user, trends_service):
        # Getting faster (speed up) = pace down = 'decreasing'
        for i in range(6):
            _make_activity(db_session, sample_user.id, i, average_speed=2.5 + 0.05 * i)
        db_session.commit()

        result = trends_service.get_metric_trend(user_id=sample_user.id, metric_type="average_speed")
        assert result["trend"]["direction"] == "decreasing"
        assert result["trend"]["slope"] < 0
        assert result["trend"]["r_squared"] > 0.9

    def test_zero_speed_activity_returns_zero_pace(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        _make_activity(db_session, sample_user.id, 1, average_speed=0.0)  # bad data
        db_session.commit()

        result = trends_service.get_metric_trend(user_id=sample_user.id, metric_type="average_speed")
        values = sorted(p["value"] for p in result["data_points"])
        assert values[0] == 0.0

    def test_distance_bucket_filter_case_insensitive(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)  # 5000m = 5k bucket
        db_session.commit()

        for bucket in ("5k", "5K"):
            result = trends_service.get_metric_trend(
                user_id=sample_user.id, metric_type="average_speed", distance_bucket=bucket
            )
            assert len(result["data_points"]) == 1

        result = trends_service.get_metric_trend(
            user_id=sample_user.id, metric_type="average_speed", distance_bucket="10k"
        )
        assert len(result["data_points"]) == 0

    def test_activity_type_filter(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        _make_activity(db_session, sample_user.id, 1, average_speed=2.78, type="Ride")
        db_session.commit()

        result = trends_service.get_metric_trend(
            user_id=sample_user.id, metric_type="average_speed", activity_type="Ride"
        )
        assert len(result["data_points"]) == 1

    def test_empty_result_shape(self, trends_service, sample_user):
        result = trends_service.get_metric_trend(user_id=sample_user.id, metric_type="average_speed")
        assert result["data_points"] == []
        assert result["aggregated_data"] == []
        assert result["trend"] == {"slope": 0, "direction": "stable", "r_squared": 0}
        assert result["unit"] == "min/km"


class TestComputedMetricTrendService:
    """Computed metrics (GAP) pass through already-pace values unchanged"""

    def test_grade_adjusted_pace_not_double_converted(self, db_session, sample_user, trends_service):
        from models.computed_metric import ComputedMetric
        activity = _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        db_session.flush()
        # GAP stored as min/km (5.5 = 5:30)
        db_session.add(ComputedMetric(
            user_id=sample_user.id, activity_id=activity.id,
            metric_type="grade_adjusted_pace", value=5.5,
        ))
        db_session.commit()

        result = trends_service.get_metric_trend(
            user_id=sample_user.id, metric_type="grade_adjusted_pace"
        )
        assert result["unit"] == "min/km"
        assert len(result["data_points"]) == 1
        assert abs(result["data_points"][0]["value"] - 5.5) < 1e-9  # unchanged


class TestMultiMetricTrend:
    def test_multi_metric_response_shape(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78, average_heartrate=150.0)
        db_session.commit()

        result = trends_service.get_multi_metric_trend(
            user_id=sample_user.id, metric_types=["average_speed", "average_heartrate"]
        )
        assert set(result["metrics"].keys()) == {"average_speed", "average_heartrate"}
        assert result["metrics"]["average_speed"]["unit"] == "min/km"
        assert result["metrics"]["average_heartrate"]["unit"] == "bpm"


class TestPercentileBands:
    def test_bands_use_display_units(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        _make_activity(db_session, sample_user.id, 1, average_speed=2.78)
        db_session.commit()

        result = trends_service.get_percentile_bands(
            user_id=sample_user.id, metric_type="average_speed", activity_type="Run"
        )
        assert result["unit"] == "min/km"
        expected = AnalyticsEngine.speed_to_pace(2.78)
        for band in result["bands"]:
            assert abs(band["p50"] - expected) < 0.001

    def test_daily_period_supported(self, db_session, sample_user, trends_service):
        _make_activity(db_session, sample_user.id, 0, average_speed=2.78)
        db_session.commit()

        result = trends_service.get_percentile_bands(
            user_id=sample_user.id, metric_type="average_speed", activity_type="Run", period="daily"
        )
        assert len(result["bands"]) == 1


class TestAvailableMetrics:
    def test_metric_names_match_activity_columns(self, db_session, sample_user, trends_service):
        metrics = trends_service.get_available_metrics(user_id=sample_user.id)
        # Names must be usable with getattr(activity, metric_type)
        assert "average_speed" in metrics
        assert "avg_speed" not in metrics
        assert "total_elevation_gain" in metrics
