"""
Tests for the Garmin sync service: dedupe (in-source + cross-source), cursor
behavior, per-activity failure isolation, and pipeline integration. The Garmin
client is stubbed; the real upload pipeline runs against the 5433 test DB.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from models.activity import Activity
from models.sync_state import SyncState
from models.user import User
from services.garmin_sync_service import (
    DUP_DISTANCE_REL_TOLERANCE,
    GarminSyncService,
)

# Minimal fake FIT bytes — the pipeline is stubbed in most tests; integration
# tests use a real FIT via the shared conftest fixture path.
FAKE_FIT = b"\x0e.FIT-fake-bytes"


def _ga_item(garmin_id, start_utc, distance_m, name="Garmin Run"):
    """Build a Garmin list-entry shaped dict."""
    return {
        "activityId": int(garmin_id),
        "activityName": name,
        "beginTimestamp": int(start_utc.timestamp() * 1000),
        "startTimeLocal": start_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "distance": distance_m,
    }


@pytest.fixture
def sync_user(db_session):
    """
    Create the dev user (id=1) that the sync router/service hardcode.
    The primary key is BIGINT with an identity default, so id must be
    assigned explicitly to land on exactly 1.
    """
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


@pytest.fixture
def stub_client():
    client = MagicMock()
    client.list_activities = AsyncMock(return_value=[])
    client.download_original_fit = AsyncMock(return_value=FAKE_FIT)
    client.pace_sleep = AsyncMock()
    return client


@pytest.fixture
def sync_service(db_session, stub_client):
    return GarminSyncService(db_session, client=stub_client)


@pytest.fixture
def stub_pipeline(monkeypatch):
    """
    Replace FileUploadService.process_upload with a recorder that inserts a
    real Activity row (source/source_id passthrough) so dedupe + cursor logic
    exercise the actual DB, while skipping FIT parsing.
    """
    imported = []

    async def _fake_process_upload(self, user_id, file_content, filename,
                                   source=None, source_id_override=None):
        source_label = source or "file_upload"
        source_id = source_id_override or f"{filename}_2026-01-01T00:00:00"
        activity = Activity(
            user_id=user_id,
            source=source_label,
            source_id=source_id,
            name=f"Imported {source_id}",
            type="Run",
            start_date=datetime(2026, 1, 1),
            start_date_local=datetime(2026, 1, 1),
            distance=1000.0,
        )
        db = self.db
        db.add(activity)
        db.commit()
        db.refresh(activity)
        imported.append(
            {
                "user_id": user_id,
                "source": source_label,
                "source_id": source_id,
                "filename": filename,
                "activity_id": activity.id,
                "bytes": file_content,
            }
        )
        return {"status": "success", "activity_id": activity.id}

    from services.file_upload_service import FileUploadService

    monkeypatch.setattr(
        FileUploadService, "process_upload", _fake_process_upload
    )
    return imported


class TestStartNormalization:
    def test_epoch_ms_preferred(self, sync_service):
        item = {"beginTimestamp": 1767225600000}  # 2026-01-01T00:00:00Z
        start = GarminSyncService._activity_start_utc(item)
        assert start is not None
        assert start.year == 2026

    def test_naive_local_falls_back_to_utc(self, sync_service):
        item = {"startTimeLocal": "2026-01-01 07:30:00"}
        start = GarminSyncService._activity_start_utc(item)
        assert start == datetime(2026, 1, 1, 7, 30, tzinfo=timezone.utc)

    def test_missing_returns_none(self, sync_service):
        assert GarminSyncService._activity_start_utc({}) is None


class TestInSourceDedupe:
    async def test_second_sync_skips_imported(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        stub_client.list_activities.return_value = [
            _ga_item(1001, datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc), 5000)
        ]
        first = await sync_service.sync(user_id=1)
        assert first["synced"] == 1

        # Same activity listed again on the next sync
        second = await sync_service.sync(user_id=1, backfill=True)
        assert second["synced"] == 0
        assert second["skipped"] == 1
        assert len(stub_pipeline) == 1

    async def test_source_and_id_written(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        stub_client.list_activities.return_value = [
            _ga_item(1002, datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc), 3200)
        ]
        await sync_service.sync(user_id=1)
        row = (
            db_session.query(Activity)
            .filter(Activity.source == "garmin", Activity.source_id == "1002")
            .first()
        )
        assert row is not None


class TestCrossSourceDuplicates:
    async def test_file_upload_twin_skipped_and_reported(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        # Existing manual upload at 07:00, 5.0 km
        db_session.add(
            Activity(
                user_id=1,
                source="file_upload",
                source_id="manual_1",
                name="Morning Run",
                type="Run",
                start_date=datetime(2026, 1, 1, 7, 0),
                start_date_local=datetime(2026, 1, 1, 7, 0),
                distance=5000.0,
            )
        )
        db_session.commit()

        # Garmin lists the same run (2 min later, 1% distance off)
        stub_client.list_activities.return_value = [
            _ga_item(2001, datetime(2026, 1, 1, 7, 2, tzinfo=timezone.utc), 5050)
        ]
        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 0
        assert report["skipped"] == 1
        assert len(report["duplicates"]) == 1
        dup = report["duplicates"][0]
        assert dup["garmin_activity_id"] == "2001"
        assert dup["existing_activity_id"] is not None
        assert dup["existing_source"] == "file_upload"
        # No download attempted for duplicates
        stub_client.download_original_fit.assert_not_awaited()

    async def test_different_activity_imports_normally(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        db_session.add(
            Activity(
                user_id=1,
                source="file_upload",
                source_id="manual_1",
                name="Morning Run",
                type="Run",
                start_date=datetime(2026, 1, 1, 7, 0),
                start_date_local=datetime(2026, 1, 1, 7, 0),
                distance=5000.0,
            )
        )
        db_session.commit()

        # Different day entirely
        stub_client.list_activities.return_value = [
            _ga_item(2002, datetime(2026, 1, 15, 7, 0, tzinfo=timezone.utc), 5100)
        ]
        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 1
        assert report["duplicates"] == []

    async def test_distance_outside_tolerance_imports(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        db_session.add(
            Activity(
                user_id=1,
                source="file_upload",
                source_id="manual_1",
                name="Morning Run",
                type="Run",
                start_date=datetime(2026, 1, 1, 7, 0),
                start_date_local=datetime(2026, 1, 1, 7, 0),
                distance=5000.0,
            )
        )
        db_session.commit()

        # Same time window but 20% distance difference → different activity
        stub_client.list_activities.return_value = [
            _ga_item(2003, datetime(2026, 1, 1, 7, 1, tzinfo=timezone.utc), 6000)
        ]
        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 1
        assert report["duplicates"] == []


class TestCursor:
    async def test_incremental_skips_old_activities(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        # Establish cursor at 2026-01-10
        stub_client.list_activities.return_value = [
            _ga_item(3001, datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc), 4000)
        ]
        await sync_service.sync(user_id=1)
        assert stub_pipeline[0]["source_id"] == "3001"

        # Next sync: one old, one new — old must be filtered by cursor
        stub_client.list_activities.return_value = [
            _ga_item(3000, datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc), 4000),
            _ga_item(3002, datetime(2026, 1, 20, 9, 0, tzinfo=timezone.utc), 4000),
        ]
        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 1
        assert stub_pipeline[-1]["source_id"] == "3002"

        state = (
            db_session.query(SyncState)
            .filter(SyncState.user_id == 1, SyncState.source == "garmin")
            .first()
        )
        assert state.last_synced_activity_start.year == 2026
        assert state.last_synced_activity_start.day == 20

    async def test_backfill_ignores_cursor(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        stub_client.list_activities.return_value = [
            _ga_item(4001, datetime(2025, 6, 1, 9, 0, tzinfo=timezone.utc), 4000),
        ]
        await sync_service.sync(user_id=1)  # cursor now at 2025-06-01

        older = [
            _ga_item(4000, datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc), 4000),
        ]
        stub_client.list_activities.return_value = older
        report = await sync_service.sync(user_id=1, backfill=True)
        assert report["synced"] == 1
        assert stub_pipeline[-1]["source_id"] == "4000"

    async def test_cursor_advances_only_when_newer(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        stub_client.list_activities.return_value = [
            _ga_item(5001, datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc), 4000)
        ]
        await sync_service.sync(user_id=1)
        state = (
            db_session.query(SyncState)
            .filter(SyncState.user_id == 1, SyncState.source == "garmin")
            .first()
        )
        cursor_after_first = state.last_synced_activity_start

        # Sync where everything is a duplicate/skip: cursor must NOT regress
        stub_client.list_activities.return_value = [
            _ga_item(5001, datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc), 4000),
            _ga_item(5000, datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc), 4000),
        ]
        await sync_service.sync(user_id=1)
        assert state.last_synced_activity_start == cursor_after_first


class TestFailureIsolation:
    async def test_download_failure_does_not_abort(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        ok_item = _ga_item(6001, datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc), 4000)
        bad_item = _ga_item(6002, datetime(2026, 4, 2, 9, 0, tzinfo=timezone.utc), 4000)

        async def download(activity_id, cache_dir=None):
            if activity_id == "6002":
                raise RuntimeError("network blip")
            return FAKE_FIT

        stub_client.download_original_fit.side_effect = download
        stub_client.list_activities.return_value = [ok_item, bad_item]

        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 1
        assert report["failed"] == 1
        assert report["failures"][0]["garmin_activity_id"] == "6002"
        assert len(stub_pipeline) == 1

    async def test_parse_failure_does_not_abort(self, sync_user, db_session, sync_service, stub_client, stub_pipeline, monkeypatch):
        from services.file_upload_service import FileUploadService

        async def _boom(self, **kwargs):
            raise ValueError("No session data found in FIT file")

        monkeypatch.setattr(FileUploadService, "process_upload", _boom)
        stub_client.list_activities.return_value = [
            _ga_item(6101, datetime(2026, 4, 3, 9, 0, tzinfo=timezone.utc), 4000)
        ]
        report = await sync_service.sync(user_id=1)
        assert report["synced"] == 0
        assert report["failed"] == 1
        assert "FIT" in report["failures"][0]["error"]

    async def test_all_failed_marks_error_status(self, sync_user, db_session, sync_service, stub_client, stub_pipeline):
        async def download(activity_id, cache_dir=None):
            raise RuntimeError("down")

        stub_client.download_original_fit.side_effect = download
        stub_client.list_activities.return_value = [
            _ga_item(6201, datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc), 4000)
        ]
        report = await sync_service.sync(user_id=1)
        assert report["failed"] == 1
        assert report["synced"] == 0
