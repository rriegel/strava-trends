"""
Enforcement tests: every data endpoint requires auth, and users can only
see their own data.

- 401: no token / garbage token on every data router.
- Cross-user isolation: user B's requests never return user A's rows.
"""
import pytest
from datetime import datetime

from models.activity import Activity
from models.route import Route
from models.activity_stream import ActivityStream
from models.user import User


@pytest.fixture
def two_users(db_session):
    """User A (owner of seeded data) and user B (the intruder)."""
    a = User(username="alice", email="alice@example.com")
    b = User(username="bob", email="bob@example.com")
    db_session.add_all([a, b])
    db_session.commit()
    db_session.refresh(a)
    db_session.refresh(b)
    return a, b


@pytest.fixture
def alice_headers(two_users):
    from utils.security import create_access_token
    a, _ = two_users
    return {"Authorization": f"Bearer {create_access_token(a.id, 0)}"}


@pytest.fixture
def bob_headers(two_users):
    from utils.security import create_access_token
    _, b = two_users
    return {"Authorization": f"Bearer {create_access_token(b.id, 0)}"}


@pytest.fixture
def alice_activity(db_session, two_users):
    a, _ = two_users
    act = Activity(
        user_id=a.id,
        source="strava",
        source_id="alice_run",
        name="Alice's Secret Run",
        type="Run",
        start_date=datetime(2026, 1, 15, 8, 0, 0),
        start_date_local=datetime(2026, 1, 15, 8, 0, 0),
        moving_time=1800,
        distance=5000.0,
    )
    db_session.add(act)
    db_session.commit()
    db_session.refresh(act)
    return act


@pytest.fixture
def alice_route(db_session, two_users, alice_activity):
    a, _ = two_users
    route = Route(
        user_id=a.id,
        name="Alice's Route",
        polyline="_y`aG~mb~N",
        polyline_hash="hash_alice_only",
        distance=5000.0,
        activity_count=1,
    )
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    alice_activity.route_id = route.id
    db_session.commit()
    return route


def _no_auth(client):
    return {"Authorization": "Bearer not-a-real-token"}


class TestUnauthenticated401:
    """Every data endpoint rejects missing/invalid tokens."""

    PATHS = [
        ("GET", "/activities/"),
        ("GET", "/activities/calendar"),
        ("GET", "/activities/99999"),
        ("GET", "/activities/99999/streams"),
        ("GET", "/activities/99999/effort"),
        ("DELETE", "/activities/99999"),
        ("GET", "/trends/metrics?metric_type=average_speed"),
        ("GET", "/trends/metrics/multi?metric_types=average_speed"),
        ("GET", "/trends/percentiles?metric_type=average_speed&activity_type=Run"),
        ("GET", "/routes"),
        ("GET", "/routes/99999"),
        ("PATCH", "/routes/99999"),
        ("GET", "/routes/99999/compare?activity_ids=1,2"),
        ("GET", "/routes/clusters/99999"),
        ("GET", "/sync/garmin/status"),
        ("GET", "/users/me"),
    ]

    @pytest.mark.parametrize("method,path", PATHS)
    def test_no_token_401(self, client, method, path):
        import httpx
        call = getattr(client, method.lower())
        response = call(path)
        assert response.status_code == 401, f"{method} {path} -> {response.status_code}"

    @pytest.mark.parametrize("method,path", PATHS)
    def test_garbage_token_401(self, client, method, path):
        call = getattr(client, method.lower())
        response = call(path, headers=_no_auth(client))
        assert response.status_code == 401, f"{method} {path} -> {response.status_code}"

    def test_upload_requires_auth(self, client):
        response = client.post(
            "/uploads/",
            files={"file": ("test.csv", b"fake", "text/csv")},
        )
        assert response.status_code == 401

    def test_sync_requires_auth(self, client):
        response = client.post("/sync/garmin")
        assert response.status_code == 401


class TestCrossUserIsolation:
    """User B never sees user A's data."""

    def test_list_activities_scoped(self, client, alice_headers, bob_headers, alice_activity):
        bob = client.get("/activities/", headers=bob_headers)
        assert bob.status_code == 200
        assert bob.json()["activities"] == []

        alice = client.get("/activities/", headers=alice_headers)
        assert alice.status_code == 200
        assert len(alice.json()["activities"]) == 1
        assert alice.json()["activities"][0]["name"] == "Alice's Secret Run"

    def test_activity_detail_scoped(self, client, alice_headers, bob_headers, alice_activity):
        bob = client.get(f"/activities/{alice_activity.id}", headers=bob_headers)
        assert bob.status_code == 404  # hidden, not 403 — don't leak existence

    def test_activity_delete_scoped(self, client, alice_headers, bob_headers, alice_activity):
        bob = client.delete(f"/activities/{alice_activity.id}", headers=bob_headers)
        assert bob.status_code == 404
        # Activity is untouched
        alice = client.get(f"/activities/{alice_activity.id}", headers=alice_headers)
        assert alice.status_code == 200

    def test_activity_streams_scoped(self, client, db_session, alice_headers, bob_headers, two_users, alice_activity):
        a, _ = two_users
        db_session.add(ActivityStream(
            user_id=a.id, activity_id=alice_activity.id, stream_type="time",
            data=[0, 1, 2], series_type="time", original_size=3,
        ))
        db_session.commit()
        bob = client.get(f"/activities/{alice_activity.id}/streams", headers=bob_headers)
        assert bob.status_code == 404

    def test_list_routes_scoped(self, client, alice_headers, bob_headers, alice_route):
        bob = client.get("/routes", headers=bob_headers)
        assert bob.status_code == 200
        assert bob.json()["routes"] == []

    def test_route_detail_scoped(self, client, alice_headers, bob_headers, alice_route):
        bob = client.get(f"/routes/{alice_route.id}", headers=bob_headers)
        assert bob.status_code == 404

    def test_route_rename_scoped(self, client, alice_headers, bob_headers, alice_route):
        bob = client.patch(
            f"/routes/{alice_route.id}", headers=bob_headers, json={"name": "Bob Was Here"}
        )
        assert bob.status_code == 404

    def test_route_compare_scoped(self, client, alice_headers, bob_headers, alice_route, alice_activity):
        bob = client.get(
            f"/routes/{alice_route.id}/compare?activity_ids={alice_activity.id}",
            headers=bob_headers,
        )
        assert bob.status_code == 404

    def test_route_fuzzy_match_never_crosses_users(self, db_session, two_users, alice_route):
        """The same GPS track run by user B must NOT match user A's route."""
        from services.route_service import find_or_create_route
        from models.route import Route

        _, b = two_users
        # Same loop geometry as Alice's route (same hash)
        activity = Activity(
            user_id=b.id,
            source="strava",
            source_id="bob_run",
            name="Bob's Run",
            type="Run",
            start_date=datetime(2026, 1, 16, 8, 0, 0),
            start_date_local=datetime(2026, 1, 16, 8, 0, 0),
            moving_time=1800,
            distance=5000.0,
        )
        db_session.add(activity)
        db_session.commit()

        # Same loop geometry as Alice's route (Ann Arbor square-ish loop)
        loop = [
            (42.2800, -83.7400), (42.2810, -83.7400), (42.2820, -83.7400), (42.2830, -83.7400),
            (42.2830, -83.7390), (42.2830, -83.7380), (42.2830, -83.7370), (42.2820, -83.7370),
            (42.2810, -83.7370), (42.2800, -83.7370), (42.2800, -83.7380), (42.2800, -83.7390),
        ]
        route = find_or_create_route(db_session, activity, loop)
        assert route is not None
        assert route.user_id == b.id
        assert route.id != alice_route.id  # B got their own route row
        assert db_session.query(Route).filter(Route.polyline_hash == "hash_alice_only").count() == 1

    def test_trends_scoped(self, client, db_session, alice_headers, bob_headers, two_users):
        a, _ = two_users
        for i in range(3):
            db_session.add(Activity(
                user_id=a.id,
                source="strava",
                source_id=f"alice_{i}",
                name=f"Run {i}",
                type="Run",
                start_date=datetime(2026, 1, i + 1, 8, 0, 0),
                start_date_local=datetime(2026, 1, i + 1, 8, 0, 0),
                moving_time=1800,
                distance=5000.0,
                average_speed=3.0,
            ))
        db_session.commit()

        bob = client.get("/trends/metrics?metric_type=average_speed", headers=bob_headers)
        assert bob.status_code == 200
        assert bob.json()["data_points"] == []

        alice = client.get("/trends/metrics?metric_type=average_speed", headers=alice_headers)
        assert alice.status_code == 200
        assert len(alice.json()["data_points"]) == 3

    def test_calendar_scoped(self, client, alice_headers, bob_headers, alice_activity):
        bob = client.get("/activities/calendar", headers=bob_headers)
        assert bob.status_code == 200
        assert bob.json()["summary"]["total_activities"] == 0

        alice = client.get("/activities/calendar", headers=alice_headers)
        assert alice.status_code == 200
        assert alice.json()["summary"]["total_activities"] == 1

    def test_sync_status_scoped(self, client, db_session, alice_headers, bob_headers, two_users):
        from models.sync_state import SyncState
        a, _ = two_users
        db_session.add(SyncState(
            user_id=a.id, source="garmin",
            last_sync_at=datetime(2026, 5, 1, 10, 0),
        ))
        db_session.commit()

        bob = client.get("/sync/garmin/status", headers=bob_headers)
        assert bob.status_code == 200
        assert bob.json()["last_sync_at"] is None

        alice = client.get("/sync/garmin/status", headers=alice_headers)
        assert alice.status_code == 200
        assert alice.json()["last_sync_at"] is not None

    def test_users_me_is_token_identity(self, client, alice_headers, two_users):
        a, _ = two_users
        me = client.get("/users/me", headers=alice_headers)
        assert me.status_code == 200
        assert me.json()["username"] == "alice"
