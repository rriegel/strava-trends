"""
Garmin sync service.

Pulls activities from the Garmin Personal API and feeds original FIT files
through the existing file upload pipeline, so streams (incl. time/distance),
route derivation, and computed metrics all behave exactly like manual uploads.

Design per spec (vault Projects/strava-trends-garmin-sync-spec.md):
- Dedupe in-source on (user_id, 'garmin', <garmin activity id>) — the unique
  constraint uq_activities_user_source_id already exists.
- Cross-source reconciliation: skip + report when an existing activity from
  another source (e.g. file_upload) looks like the same activity
  (|start_time delta| < 5 min AND |distance delta| < 5%).
- Cursor = last synced activity start time; advances only after the batch
  commits. Per-activity failures are logged-and-skipped, never fatal.
- FIT cache dir: re-syncs never re-download a file already fetched.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from models.activity import Activity
from models.sync_state import SyncState
from services.file_upload_service import FileUploadService
from services.garmin_client import GarminClient, GarminKeyError

logger = logging.getLogger(__name__)

# Cross-source duplicate tolerance
DUP_START_TOLERANCE = timedelta(minutes=5)
DUP_DISTANCE_REL_TOLERANCE = 0.05  # 5%

# Fetch detail for activities listed within this window behind the cursor
# edge (list summaries can shift slightly between calls; keep it simple).
CURSOR_OVERLAP = timedelta(minutes=10)


class GarminSyncService:
    def __init__(self, db: Session, client: Optional[GarminClient] = None):
        self.db = db
        self.client = client or GarminClient()

    # ------------------------------------------------------------------ public

    async def sync(
        self,
        user_id: int,
        backfill: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a sync. Incremental by default (activities newer than the stored
        cursor). backfill=True ignores the cursor (pulls full history, bounded
        by `limit` if given).

        Returns a report dict; never raises for per-activity failures.
        Raises GarminKeyError / GarminApiError for auth/transport problems.
        """
        state = SyncState.for_user(self.db, user_id)

        report: Dict[str, Any] = {
            "status": "success",
            "synced": 0,
            "skipped": 0,
            "failed": 0,
            "duplicates": [],  # cross-source hits, for the reconciliation UI
            "failures": [],    # per-activity error entries
        }
        report["cursor_before"] = (
            state.last_synced_activity_start.isoformat()
            if state.last_synced_activity_start
            else None
        )

        listed = await self.client.list_activities(limit=limit if backfill else None)
        since = None if backfill else state.last_synced_activity_start
        # DB stores naive datetimes; normalize the cursor to naive-UTC so all
        # comparisons stay in one regime.
        if since is not None and since.tzinfo is not None:
            since = since.replace(tzinfo=None)

        pending: List[Dict[str, Any]] = []
        for item in listed:
            start_utc = self._activity_start_utc(item)
            if start_utc is None:
                report["failures"].append(
                    {
                        "garmin_activity_id": item.get("activityId"),
                        "error": "list entry missing usable start time",
                    }
                )
                report["failed"] += 1
                continue
            if since and start_utc.replace(tzinfo=None) <= since - CURSOR_OVERLAP:
                continue
            pending.append(item)

        cache_dir = self._fit_cache_dir()

        for item in pending:
            garmin_id = str(item.get("activityId"))
            start_utc = self._activity_start_utc(item)

            # 1. In-source idempotency
            if self._already_imported(user_id, garmin_id):
                report["skipped"] += 1
                continue

            # 2. Cross-source duplicate check (file_upload twin etc.)
            duplicate = self._find_cross_source_duplicate(
                user_id, start_utc, item.get("distance")
            )
            if duplicate:
                report["duplicates"].append(
                    {
                        "garmin_activity_id": garmin_id,
                        "garmin_start": start_utc.isoformat(),
                        "garmin_distance": item.get("distance"),
                        "garmin_name": item.get("activityName"),
                        "existing_activity_id": duplicate.id,
                        "existing_source": duplicate.source,
                        "existing_name": duplicate.name,
                    }
                )
                report["skipped"] += 1
                continue

            # 3. Download original FIT (cache-aware) + feed the pipeline
            try:
                fit_bytes = await self.client.download_original_fit(
                    garmin_id, cache_dir=cache_dir
                )
            except Exception as exc:  # per-activity failures never abort the sync
                logger.warning("Garmin FIT download failed for %s: %s", garmin_id, exc)
                report["failures"].append(
                    {"garmin_activity_id": garmin_id, "error": str(exc)}
                )
                report["failed"] += 1
                continue

            try:
                result = await FileUploadService(self.db).process_upload(
                    user_id=user_id,
                    file_content=fit_bytes,
                    filename=f"{garmin_id}.fit",
                    source="garmin",
                    source_id_override=garmin_id,
                )
            except Exception as exc:
                logger.warning("Garmin import failed for %s: %s", garmin_id, exc)
                report["failures"].append(
                    {"garmin_activity_id": garmin_id, "error": str(exc)}
                )
                report["failed"] += 1
                continue

            if result.get("status") == "duplicate":
                # Raced with a concurrent import of the same garmin id
                report["skipped"] += 1
                continue

            report["synced"] += 1
            await self.client.pace_sleep()

        # 4. Cursor advances only after the whole batch was processed.
        # _newest_pending_start returns naive-UTC (DB regime).
        newest = self._newest_pending_start(pending)
        if newest and (
            state.last_synced_activity_start is None
            or newest > state.last_synced_activity_start
        ):
            state.last_synced_activity_start = newest
        state.last_sync_at = datetime.now(timezone.utc)
        self.db.commit()

        report["cursor_after"] = (
            state.last_synced_activity_start.isoformat()
            if state.last_synced_activity_start
            else None
        )
        return report

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _activity_start_utc(item: Dict[str, Any]) -> Optional[datetime]:
        """
        Normalize a list-entry start time to an aware UTC datetime.

        Prefer beginTimestamp (epoch millis, unambiguous). Fall back to
        startTimeLocal (timezone-naive, device-local) interpreted as UTC so
        cursor comparisons stay monotone (documented in the spec's to-verify).
        """
        epoch_ms = item.get("beginTimestamp")
        if epoch_ms:
            return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        local = item.get("startTimeLocal") or item.get("startTimeGMT")
        if not local:
            return None
        try:
            return datetime.fromisoformat(str(local)).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _already_imported(self, user_id: int, garmin_id: str) -> bool:
        return (
            self.db.query(Activity)
            .filter(
                Activity.user_id == user_id,
                Activity.source == "garmin",
                Activity.source_id == garmin_id,
            )
            .first()
            is not None
        )

    def _find_cross_source_duplicate(
        self,
        user_id: int,
        start_utc: Optional[datetime],
        garmin_distance_m: Optional[float],
    ) -> Optional[Activity]:
        """Same activity imported under another source (file_upload twin)."""
        if start_utc is None:
            return None
        window_start = start_utc - DUP_START_TOLERANCE
        window_end = start_utc + DUP_START_TOLERANCE
        # DB start_date is timezone-naive; compare in naive-UTC space.
        candidates = (
            self.db.query(Activity)
            .filter(
                Activity.user_id == user_id,
                Activity.source != "garmin",
                Activity.start_date >= window_start.replace(tzinfo=None),
                Activity.start_date <= window_end.replace(tzinfo=None),
            )
            .all()
        )
        for candidate in candidates:
            if garmin_distance_m and candidate.distance:
                delta = abs(float(candidate.distance) - float(garmin_distance_m))
                if delta / float(garmin_distance_m) <= DUP_DISTANCE_REL_TOLERANCE:
                    return candidate
            else:
                # No comparable distance on one side: time-window hit alone is
                # strong enough for a single-user history (start times are
                # effectively unique per activity).
                return candidate
        return None

    @staticmethod
    def _newest_pending_start(pending: List[Dict[str, Any]]) -> Optional[datetime]:
        """Newest pending start as naive-UTC (the DB storage regime)."""
        starts = [
            GarminSyncService._activity_start_utc(item) for item in pending
        ]
        starts = [
            s.replace(tzinfo=None) for s in starts if s is not None
        ]
        return max(starts) if starts else None

    @staticmethod
    def _fit_cache_dir() -> str:
        if settings.garmin_fit_cache_dir:
            return settings.garmin_fit_cache_dir
        # Default: <backend>/data/garmin_fit_cache (services/ is one level deep)
        import os

        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(backend_root, "data", "garmin_fit_cache")
