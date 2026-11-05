"""
Endpoint tests for the Garmin sync router.
The GarminClient is stubbed at the service boundary; DB is the 5433 test DB.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from models.activity import Activity
from models.sync_state import SyncState
from models.user import User
from services.garmin_sync_service import GarminSyncService

FAKE_FIT = b"\x0e.FIT-fake-bytes"


@pytest.fixture
def garmin_env_on(monkeypatch):
    monkeypatch.setattr("config.settings.garmin_api_key", "test-key")
    monkeypatch.setattr("config.settings.garmin_api_key_expires_at", "2099-01-01")


@pytest.fixture
def stub_sync(monkeypatch):
    """
    Patch GarminSyncService.sync with a recorder returning a canned report.
    Individual tests override the return value.
    """
    report = {
        "status": "success",
        "synced": 2,
        "skipped": 1,
        "failed": 0,
        "duplicates": [],
        "failures": [],
        "cursor_before": None,
        "cursor_after": "2026-05-01T09:00:00+00:00",
    }
    calls = []

    async def _fake_sync(self, user_id, backfill=False, limit=None):
        calls.append({"user_id": user_id, "backfill": backfill, "limit": limit})
        return report

    monkeypatch.setattr(GarminSyncService, "sync", _fake_sync)
    return {"calls": calls, "report": report}


def _seed_state(db_session, start=None):
    state = SyncState(
        user_id=1,
        source="garmin",
        last_synced_activity_start=start,
        last_sync_at=datetime(2026, 5, 1, 10, 0),
    )
    db_session.add(state)
    db_session.commit()
    return state


@pytest.fixture
def sync_user(db_session):
    """Create the dev user (id=1) that the sync router hardcodes."""
    from sqlalchemy import text

    user = User(
        strava_athlete_id=None,
        username="syncuser",
        firstname="Sync",
        lastname="User",
        email="sync@example.com",
    )
    db_session.add(user)
    db_session.flush()
    db_session.execute(
        text("SELECT setval(pg_get_serial_sequence('users','id'), :v)"),
        {"v": max(user.id, 1)},
    )
    db_session.commit()
    db_session.refresh(user)
    assert user.id == 1, f"dev user must be id 1, got {user.id}"
    return user


@pytest.fixture(autouse=True)
def _isolate_garmin_env(monkeypatch):
    """
    Tests must never see the developer's real key from backend/.env:
    pydantic-settings loads it into the settings singleton at import time.
    """
    monkeypatch.setattr("config.settings.garmin_api_key", "")
    monkeypatch.setattr("config.settings.garmin_api_key_expires_at", "")
    yield


class TestSyncEndpoint:
    def test_sync_requires_key(self, client, db_session):
        response = client.post("/sync/garmin")
        assert response.status_code == 423
        assert "not configured" in response.json()["detail"]

    def test_sync_expired_key_423(self, client, db_session, monkeypatch):
        monkeypatch.setattr("config.settings.garmin_api_key", "k")
        monkeypatch.setattr("config.settings.garmin_api_key_expires_at", "2020-01-01")
        response = client.post("/sync/garmin")
        assert response.status_code == 423
        assert "EXPIRED" in response.json()["detail"]

    def test_sync_success_returns_report(self, client, sync_user, db_session, garmin_env_on, stub_sync):
        response = client.post("/sync/garmin")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["synced"] == 2
        assert body["skipped"] == 1
        assert stub_sync["calls"][0]["backfill"] is False

    def test_sync_backfill_params_forwarded(self, client, sync_user, db_session, garmin_env_on, stub_sync):
        response = client.post("/sync/garmin?backfill=true&limit=50")
        assert response.status_code == 200
        assert stub_sync["calls"][0]["backfill"] is True
        assert stub_sync["calls"][0]["limit"] == 50

    def test_sync_reports_error_when_all_failed(self, client, sync_user, db_session, garmin_env_on, stub_sync):
        stub_sync["report"].update({"synced": 0, "skipped": 0, "failed": 3, "failures": [{"garmin_activity_id": "1", "error": "x"}]})
        response = client.post("/sync/garmin")
        assert response.status_code == 200
        assert response.json()["status"] == "error"

    def test_sync_transport_failure_502(self, client, sync_user, db_session, garmin_env_on, monkeypatch):
        from services.garmin_client import GarminApiError

        async def _boom(self, user_id, backfill=False, limit=None):
            raise GarminApiError("Garmin unreachable")

        monkeypatch.setattr(GarminSyncService, "sync", _boom)
        response = client.post("/sync/garmin")
        assert response.status_code == 502


class TestImportSingleEndpoint:
    def test_import_single_success(self, client, sync_user, db_session, monkeypatch):
        report = {"status": "success", "synced": 1, "skipped": 0, "failed": 0,
                  "duplicates": [], "failures": []}

        async def _fake(self, user_id, garmin_id):
            assert garmin_id == "9999"
            return report

        monkeypatch.setattr(GarminSyncService, "import_single", _fake)
        response = client.post("/sync/garmin/9999")
        assert response.status_code == 200
        assert response.json()["synced"] == 1

    def test_import_single_failure_502(self, client, sync_user, db_session, monkeypatch):
        async def _fake(self, user_id, garmin_id):
            return {"status": "error", "synced": 0, "skipped": 0, "failed": 1,
                    "duplicates": [],
                    "failures": [{"garmin_activity_id": garmin_id, "error": "boom"}]}

        monkeypatch.setattr(GarminSyncService, "import_single", _fake)
        response = client.post("/sync/garmin/9998")
        assert response.status_code == 502


class TestStatusEndpoint:
    def test_status_unconfigured(self, client, db_session, monkeypatch):
        monkeypatch.setattr("config.settings.garmin_api_key", "")
        response = client.get("/sync/garmin/status")
        assert response.status_code == 200
        body = response.json()
        assert body["key_configured"] is False
        assert body["last_sync_at"] is None

    def test_status_with_state_and_expiry(self, client, sync_user, db_session, garmin_env_on):
        _seed_state(
            db_session,
            start=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc).replace(tzinfo=None),
        )
        response = client.get("/sync/garmin/status")
        assert response.status_code == 200
        body = response.json()
        assert body["key_configured"] is True
        assert body["key_expired"] is False
        assert body["key_days_left"] is not None and body["key_days_left"] > 300
        assert body["last_sync_at"] is not None
        assert body["cursor"] is not None

    def test_status_expiry_warning_window(self, client, sync_user, db_session, monkeypatch):
        # 5 days out → warning true
        monkeypatch.setattr("config.settings.garmin_api_key", "k")
        monkeypatch.setattr("config.settings.garmin_api_key_expires_at", "2099-01-01")
        # Freeze "today" indirectly: choose an expiry that is ~5 days ahead
        from datetime import date, timedelta

        soon = (date.today() + timedelta(days=5)).isoformat()
        monkeypatch.setattr("config.settings.garmin_api_key_expires_at", soon)
        response = client.get("/sync/garmin/status")
        body = response.json()
        assert body["key_warning"] is True
        assert body["key_days_left"] == 5

    def test_status_expired_flag(self, client, sync_user, db_session, monkeypatch):
        monkeypatch.setattr("config.settings.garmin_api_key", "k")
        monkeypatch.setattr("config.settings.garmin_api_key_expires_at", "2020-06-01")
        response = client.get("/sync/garmin/status")
        body = response.json()
        assert body["key_expired"] is True
        assert body["key_days_left"] < 0
