"""
Garmin sync endpoints.

POST /sync/garmin         — run a sync (incremental by default; ?backfill=true
                            for the initial history pull, optional &limit=N)
GET  /sync/garmin/status  — last-sync info + key expiry countdown

Identity comes from the JWT access token; every endpoint is scoped to the
authenticated user.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.sync_state import SyncState
from models.user import User
from routers.auth import get_current_user
from services.garmin_client import (
    GarminClient,
    GarminApiError,
    GarminKeyError,
    assert_key_usable,
    parse_key_expiry,
)
from services.garmin_sync_service import GarminSyncService

router = APIRouter()

# Keys expire (max 1 year) and Garmin emails ~1 week ahead — surface the
# countdown from this threshold onward.
EXPIRY_WARNING_DAYS = 7


@router.post("/garmin")
async def sync_garmin(
    backfill: bool = Query(False, description="Ignore cursor; pull full history"),
    limit: int | None = Query(None, ge=1, le=2000, description="Cap for backfill"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run a Garmin sync. Synchronous; returns the sync report."""
    try:
        assert_key_usable()
    except GarminKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        )

    service = GarminSyncService(db)
    try:
        report = await service.sync(user_id=current_user.id, backfill=backfill, limit=limit)
    except (GarminKeyError, GarminApiError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    if report["failed"] and not report["synced"] and not report["skipped"]:
        report["status"] = "error"
    return report


@router.post("/garmin/{garmin_activity_id}")
async def import_single_garmin_activity(
    garmin_activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import ONE specific Garmin activity (duplicate reconciliation:
    delete the manual twin first, then call this to import the original).
    """
    try:
        assert_key_usable()
    except GarminKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(exc),
        )

    service = GarminSyncService(db)
    try:
        report = await service.import_single(current_user.id, garmin_activity_id)
    except (GarminKeyError, GarminApiError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    if report["failed"]:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=report["failures"][0]["error"] if report["failures"] else "Import failed",
        )
    return report


@router.get("/garmin/status")
async def garmin_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Last-sync info + API key expiry countdown for the UI badges."""
    state = (
        db.query(SyncState)
        .filter(SyncState.user_id == current_user.id, SyncState.source == "garmin")
        .first()
    )

    expiry = parse_key_expiry(settings.garmin_api_key_expires_at)
    key_configured = bool(settings.garmin_api_key)

    days_left: int | None = None
    if expiry:
        days_left = (expiry - date.today()).days

    expired = bool(expiry and days_left is not None and days_left < 0)
    warn = key_configured and (
        expiry is None
        or (days_left is not None and days_left <= EXPIRY_WARNING_DAYS)
    )

    return {
        "key_configured": key_configured,
        "key_expires_at": expiry.isoformat() if expiry else None,
        "key_days_left": days_left,
        "key_expired": expired,
        "key_warning": warn and not expired,
        "last_sync_at": state.last_sync_at.isoformat() if state and state.last_sync_at else None,
        "cursor": (
            state.last_synced_activity_start.isoformat()
            if state and state.last_synced_activity_start
            else None
        ),
    }
