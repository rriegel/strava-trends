"""Tests for GET /routes/{route_id}/compare (route comparison endpoint)."""
import pytest
from datetime import datetime

from models.route import Route
from models.activity import Activity
from models.activity_stream import ActivityStream


@pytest.fixture
def sample_route(db_session, sample_user):
    """Route running north, start (40.00, -74.00) -> end (40.05, -74.00)."""
    route = Route(
        user_id=sample_user.id,
        name="Test Route",
        distance=5000.0,
        elevation_gain=40.0,
        activity_count=2,
        cluster_id=None,
        start_lat=40.00, start_lng=-74.00,
        end_lat=40.05, end_lng=-74.00,
        polyline="",
        polyline_hash="testhash_route_compare_0001",
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    return route


def _add_activity_with_streams(db_session, user_id, route, idx, with_time=True):
    """Activity on the route with latlng track heading north + streams."""
    act = Activity(
        user_id=user_id,
        source="file_upload",
        source_id=f"file_{idx}",
        name=f"Compare Run {idx}",
        type="Run",
        sport_type="Run",
        start_date=datetime(2026, 10, idx + 1, 8, 0, 0),
        start_date_local=datetime(2026, 10, idx + 1, 8, 0, 0),
        moving_time=1500,
        elapsed_time=1600,
        distance=5000.0,
        total_elevation_gain=40.0,
        average_speed=3.33,
        max_speed=4.0,
        has_heartrate=False,
        route_id=route.id,
    )
    db_session.add(act)
    db_session.flush()

    # Northward 5km track, 11 points, ~500m apart
    latlng = [[40.00 + i * 0.0045, -74.00] for i in range(11)]
    db_session.add(ActivityStream(
        user_id=user_id, activity_id=act.id, stream_type="latlng",
        data=latlng, series_type="time", original_size=len(latlng),
    ))
    if with_time:
        times = [i * 150 for i in range(11)]  # 150s per 500m => 5:00/km
        distances = [i * 500.0 for i in range(11)]
        db_session.add(ActivityStream(
            user_id=user_id, activity_id=act.id, stream_type="time",
            data=times, series_type="time", original_size=len(times),
        ))
        db_session.add(ActivityStream(
            user_id=user_id, activity_id=act.id, stream_type="distance",
            data=distances, series_type="time", original_size=len(distances),
        ))
    db_session.commit()
    return act


class TestCompareEndpoint:
    def test_full_payload(self, client, db_session, sample_user, sample_route, auth_headers):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        a2 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=2)

        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={a1.id},{a2.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["route"]["id"] == sample_route.id
        assert len(data["activities"]) == 2

        first = data["activities"][0]
        assert first["id"] == a1.id
        assert first["summary"]["name"] == f"Compare Run 1"
        assert first["summary"]["average_heartrate"] is None
        assert first["direction_reversed"] is False

        # Track decimated but present
        assert 2 <= len(first["track"]) <= 500
        assert first["track"][0] == [40.0, -74.0]

        # Race plot: 11-point curve, 0->7500s... no: 150s/500m => 1500s total
        assert first["race_plot"] is not None
        assert first["race_plot"]["distances"] == [i * 500.0 for i in range(11)]
        assert first["race_plot"]["elapsed_seconds"] == [i * 150 for i in range(11)]

        # Splits at the default 1000 m checkpoints: 5 segments at 5:00/km
        assert first["splits"] is not None
        assert len(first["splits"]) == 5
        for s in first["splits"]:
            assert s["pace_s_per_km"] == pytest.approx(300, rel=0.05)

    def test_custom_checkpoint_interval(
        self, client, db_session, sample_user, sample_route, auth_headers
    ):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        a2 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=2)

        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={a1.id},{a2.id}&checkpoint_interval_m=400",
            headers=auth_headers,
        )
        assert response.status_code == 200
        first = response.json()["activities"][0]
        # 5000m at 400m checkpoints => 12 full + partial final = 13
        assert len(first["splits"]) == 13
        assert first["splits"][0]["end_m"] == 400.0
        for s in first["splits"][:-1]:
            assert s["pace_s_per_km"] == pytest.approx(300, rel=0.05)

    def test_checkpoint_interval_validation(
        self, client, db_session, sample_user, sample_route, auth_headers
    ):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        a2 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=2)
        base = f"/routes/{sample_route.id}/compare?activity_ids={a1.id},{a2.id}"

        response = client.get(
            f"{base}&checkpoint_interval_m=0",
            headers=auth_headers,
        )
        assert response.status_code == 422
        response = client.get(
            f"{base}&checkpoint_interval_m=6000",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_activity_without_time_streams_still_gets_track_and_summary(
        self, client, db_session, sample_user, sample_route, auth_headers
    ):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        a2 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=2, with_time=False)

        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={a1.id},{a2.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        acts = {a["id"]: a for a in response.json()["activities"]}
        assert acts[a2.id]["race_plot"] is None
        assert acts[a2.id]["splits"] is None
        assert len(acts[a2.id]["track"]) > 0  # map overlay still works

    def test_reverse_run_omits_race_plot(
        self, client, db_session, sample_user, sample_route, auth_headers
    ):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        # a2 runs the route southward (reversed relative to start->end north)
        a2 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=2)
        # Overwrite a2's latlng with a southward track
        south = [[40.05 - i * 0.0045, -74.00] for i in range(11)]
        from database import get_db  # noqa: F401
        stream = (
            db_session.query(ActivityStream)
            .filter_by(activity_id=a2.id, stream_type="latlng")
            .first()
        )
        stream.data = south
        db_session.commit()

        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={a1.id},{a2.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        acts = {a["id"]: a for a in response.json()["activities"]}
        assert acts[a2.id]["direction_reversed"] is True
        assert acts[a2.id]["race_plot"] is None

    def test_single_activity_rejected(self, client, sample_user, sample_route, auth_headers):
        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids=1",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_six_activities_rejected(self, client, db_session, sample_user, sample_route, auth_headers):
        acts = [_add_activity_with_streams(db_session, sample_user.id, sample_route, idx=i) for i in range(6)]
        ids = ",".join(str(a.id) for a in acts)
        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={ids}",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_activity_not_on_route_404s(self, client, db_session, sample_user, sample_route, auth_headers):
        a1 = _add_activity_with_streams(db_session, sample_user.id, sample_route, idx=1)
        # an activity on a DIFFERENT (nonexistent) route
        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids={a1.id},999999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_route_404(self, client, sample_user, auth_headers):
        response = client.get(
            "/routes/999999/compare?activity_ids=1,2",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_garbage_ids_422(self, client, sample_user, sample_route, auth_headers):
        response = client.get(
            f"/routes/{sample_route.id}/compare?activity_ids=abc,def",
            headers=auth_headers,
        )
        assert response.status_code == 422