"""
Tests for the /activities/calendar endpoint (heatmap data + summary stats).
"""
from datetime import datetime, timedelta

import pytest

from models.activity import Activity


def _add_activity(db_session, user_id, day: datetime, distance=5000.0, moving_time=1800):
    activity = Activity(
        user_id=user_id,
        source="strava",
        source_id=f"cal_{day.isoformat()}_{distance}",
        name="Calendar Run",
        type="Run",
        sport_type="Run",
        start_date=day,
        start_date_local=day,
        moving_time=moving_time,
        distance=distance,
    )
    db_session.add(activity)
    return activity


class TestCalendarEndpoint:
    """Test /activities/calendar heatmap + summary"""

    def test_empty_calendar(self, client, sample_user):
        response = client.get("/activities/calendar")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["summary"]["total_activities"] == 0
        assert data["summary"]["total_distance"] == 0
        assert data["summary"]["longest_streak"] == 0
        assert data["summary"]["most_active_day"] == ""

    def test_summary_totals(self, client, db_session, sample_user):
        base = datetime(2024, 3, 1, 8, 0, 0)
        # 3 activities on one day + 1 on another
        _add_activity(db_session, sample_user.id, base, distance=5000, moving_time=1800)
        _add_activity(db_session, sample_user.id, base + timedelta(hours=2), distance=8000, moving_time=2400)
        _add_activity(db_session, sample_user.id, base + timedelta(hours=4), distance=3000, moving_time=900)
        _add_activity(db_session, sample_user.id, base + timedelta(days=1), distance=10000, moving_time=3600)
        db_session.commit()

        response = client.get("/activities/calendar")
        assert response.status_code == 200
        data = response.json()

        summary = data["summary"]
        assert summary["total_activities"] == 4
        assert summary["total_distance"] == 26000.0
        assert summary["total_moving_time"] == 8700
        # Two consecutive days -> streak of 2
        assert summary["longest_streak"] == 2
        # Day 1 has 3 activities vs 1 on day 2
        assert summary["most_active_day"] == base.strftime("%A")

    def test_longest_streak_with_gaps(self, client, db_session, sample_user):
        # Streak of 3 days, gap, then streak of 2
        base = datetime(2024, 5, 1, 8, 0, 0)
        for offset in (0, 1, 2, 5, 6):
            _add_activity(db_session, sample_user.id, base + timedelta(days=offset))
        db_session.commit()

        response = client.get("/activities/calendar")
        data = response.json()
        assert data["summary"]["longest_streak"] == 3

    def test_summary_respects_date_range(self, client, db_session, sample_user):
        base = datetime(2024, 6, 1, 8, 0, 0)
        _add_activity(db_session, sample_user.id, base)
        _add_activity(db_session, sample_user.id, base + timedelta(days=30))
        db_session.commit()

        response = client.get(
            "/activities/calendar?start_date=2024-06-01T00:00:00&end_date=2024-06-05T23:59:59"
        )
        data = response.json()
        assert data["summary"]["total_activities"] == 1
        assert data["summary"]["longest_streak"] == 1
