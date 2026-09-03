"""
Tests for the route building service (route_service.py) and its
integration with the upload pipeline and the /routes API.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.activity import Activity
from models.activity_stream import ActivityStream
from models.route import Route
from models.user import User
from services.route_service import (
    backfill_routes,
    build_route_for_activity,
    canonicalize,
    find_or_create_route,
    path_length_m,
    polyline_hash_for,
    symmetric_path_distance_m,
)


# A square-ish loop in Ann Arbor, ~1.1km. Corner spacing (~330m) is far
# above the 5m simplification tolerance, so DP keeps the corners — this
# is the shape of real running loops.
LOOP = [
    (42.2800, -83.7400), (42.2810, -83.7400), (42.2820, -83.7400), (42.2830, -83.7400),
    (42.2830, -83.7390), (42.2830, -83.7380), (42.2830, -83.7370), (42.2820, -83.7370),
    (42.2810, -83.7370), (42.2800, -83.7370), (42.2800, -83.7380), (42.2800, -83.7390),
]


def jittered_loop(seed: int = 42, amplitude: float = 0.00004) -> list:
    """The same loop recorded by a different device: sub-5m jitter and
    duplicate points from GPS holds."""
    import random

    rng = random.Random(seed)
    pts = [
        (lat + rng.uniform(-amplitude, amplitude), lng + rng.uniform(-amplitude, amplitude))
        for lat, lng in LOOP
    ]
    return pts + pts[:3]


def make_activity(user, **overrides) -> Activity:
    defaults = dict(
        user_id=user.id,
        source="file_upload",
        source_id="test-source",
        name="Morning Run",
        type="Run",
        sport_type="Run",
        start_date=datetime(2026, 1, 15, 8, 0, 0),
        start_date_local=datetime(2026, 1, 15, 8, 0, 0),
        moving_time=1800,
        elapsed_time=1850,
        distance=5200.0,
        total_elevation_gain=40.0,
        average_speed=2.9,
        max_speed=3.5,
    )
    defaults.update(overrides)
    return Activity(**defaults)


def add_latlng_stream(db, activity, coords) -> ActivityStream:
    stream = ActivityStream(
        user_id=activity.user_id,
        activity_id=activity.id,
        stream_type="latlng",
        data=[[c[0], c[1]] for c in coords],
        series_type="time",
        original_size=len(coords),
    )
    db.add(stream)
    db.commit()
    return stream


@pytest.fixture
def user(db_session):
    u = User(
        strava_athlete_id=987654321,
        username="routetest",
        email="route@test.com",
        access_token="t",
        refresh_token="t",
        token_expires_at=datetime.now(),
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


class TestCanonicalization:
    def test_rejects_short_tracks(self):
        assert canonicalize(LOOP[:5]) == []

    def test_rejects_tracks_below_min_distance(self):
        # 9 tiny movements around a point = under 200m total
        tiny = [(42.28 + i * 1e-6, -83.74 + i * 1e-6) for i in range(30)]
        assert canonicalize(tiny) == []

    def test_accepts_real_loop(self):
        assert len(canonicalize(LOOP)) >= 2

    def test_fuzzy_distance_same_loop_small_jitter_below_threshold(self):
        """Core matching guarantee: same loop, different device → distance
        well under the 50m threshold."""
        d = symmetric_path_distance_m(canonicalize(LOOP), canonicalize(jittered_loop()))
        assert d < 50.0

    def test_fuzzy_distance_different_route_far_above_threshold(self):
        """A route shifted 1km must NOT match."""
        shifted = [(lat, lng + 0.01) for lat, lng in LOOP]
        d = symmetric_path_distance_m(canonicalize(LOOP), canonicalize(shifted))
        assert d > 300.0

    def test_polyline_hash_is_deterministic(self):
        _, h1 = polyline_hash_for(LOOP)
        _, h2 = polyline_hash_for(list(LOOP))  # fresh list, same values
        assert h1 == h2


class TestFindOrCreateRoute:
    def test_creates_route_with_metadata(self, db_session, user):
        activity = make_activity(user)
        db_session.add(activity)
        db_session.commit()

        route = find_or_create_route(db_session, activity, LOOP)
        db_session.commit()

        assert route is not None
        assert route.id is not None
        assert route.activity_count == 1
        assert route.name == "Morning Run"
        assert route.distance is not None and route.distance > 500
        assert route.elevation_gain == 40.0
        assert float(route.start_lat) == pytest.approx(LOOP[0][0], abs=1e-4)
        assert activity.route_id == route.id

    def test_second_recording_matches_same_route_via_fuzzy(self, db_session, user):
        """The key behavior: a re-run of the same loop (jittered) lands on
        the SAME route row instead of creating a near-duplicate."""
        a1 = make_activity(user, source_id="run-1")
        db_session.add(a1)
        db_session.commit()
        r1 = find_or_create_route(db_session, a1, LOOP)
        db_session.commit()

        a2 = make_activity(user, source_id="run-2")
        db_session.add(a2)
        db_session.commit()
        r2 = find_or_create_route(db_session, a2, jittered_loop(seed=7))
        db_session.commit()

        assert r2.id == r1.id
        assert r1.activity_count == 2
        assert a2.route_id == r1.id

    def test_different_route_creates_separate_row(self, db_session, user):
        a1 = make_activity(user, source_id="run-1")
        db_session.add(a1)
        db_session.commit()
        r1 = find_or_create_route(db_session, a1, LOOP)
        db_session.commit()

        shifted = [(lat, lng + 0.01) for lat, lng in LOOP]
        a2 = make_activity(user, source_id="run-2")
        db_session.add(a2)
        db_session.commit()
        r2 = find_or_create_route(db_session, a2, shifted)
        db_session.commit()

        assert r2.id != r1.id
        assert r1.activity_count == 1
        assert r2.activity_count == 1

    def test_rolling_average_metadata_on_match(self, db_session, user):
        """Distance/elevation refresh as rolling averages across matches."""
        a1 = make_activity(user, source_id="run-1", distance=5000.0, total_elevation_gain=40.0)
        db_session.add(a1)
        db_session.commit()
        r1 = find_or_create_route(db_session, a1, LOOP)
        db_session.commit()
        d1 = r1.distance

        # Second recording with different measured distance
        a2 = make_activity(user, source_id="run-2", distance=7000.0, total_elevation_gain=60.0)
        db_session.add(a2)
        db_session.commit()
        r2 = find_or_create_route(db_session, a2, jittered_loop(seed=3))
        db_session.commit()

        assert r2.id == r1.id
        assert r2.distance != d1  # refreshed
        # Rolling average of the two recordings' *track* lengths — not the
        # activity's recorded distance (the 5m-simplified canonical paths
        # cut corners, so track length < recorded distance by design).
        track_len_2 = path_length_m(canonicalize(jittered_loop(seed=3)))
        assert float(r2.distance) == pytest.approx((float(d1) + track_len_2) / 2, rel=0.02)
        assert float(r2.elevation_gain) == pytest.approx(50.0, rel=0.01)


class TestBuildRouteForActivity:
    def test_returns_none_without_stream(self, db_session, user):
        activity = make_activity(user)
        db_session.add(activity)
        db_session.commit()
        assert build_route_for_activity(db_session, activity) is None

    def test_uses_stored_stream(self, db_session, user):
        activity = make_activity(user)
        db_session.add(activity)
        db_session.commit()
        add_latlng_stream(db_session, activity, LOOP)

        route = build_route_for_activity(db_session, activity)
        db_session.commit()
        assert route is not None
        assert route.activity_count == 1


class TestBackfill:
    def test_backfill_creates_routes_and_is_idempotent(self, db_session, user):
        # Two recordings of the same loop + one GPS-less activity
        for i, coords in enumerate([LOOP, jittered_loop(seed=11)]):
            a = make_activity(user, source_id=f"run-{i}")
            db_session.add(a)
            db_session.commit()
            add_latlng_stream(db_session, a, coords)

        stats1 = backfill_routes(db_session)
        assert stats1["activities_scanned"] == 2
        assert stats1["routes_created"] == 1  # both merged into one route
        assert stats1["routes_matched"] == 1

        routes = db_session.query(Route).all()
        assert len(routes) == 1
        assert routes[0].activity_count == 2

        # Idempotence: re-running must not double counts or add routes
        stats2 = backfill_routes(db_session)
        assert stats2["routes_created"] == 0
        assert stats2["routes_matched"] == 2
        assert db_session.query(Route).count() == 1
        assert db_session.query(Route).first().activity_count == 2


class TestRoutesEndpoint:
    def test_list_routes_returns_built_route(self, client, db_session, user):
        activity = make_activity(user)
        db_session.add(activity)
        db_session.commit()
        add_latlng_stream(db_session, activity, LOOP)
        build_route_for_activity(db_session, activity)
        db_session.commit()

        response = client.get("/routes")
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        r = data["routes"][0]
        assert r["name"] == "Morning Run"
        assert r["activity_count"] == 1
        assert r["polyline"]  # encoded polyline present for the map

    def test_list_routes_empty(self, client, db_session, user):
        response = client.get("/routes")
        assert response.status_code == 200
        assert response.json()["routes"] == []
