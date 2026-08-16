from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User

router = APIRouter()

@router.get("/me")
async def get_user_profile(db: Session = Depends(get_db)):
    """Get current user's profile"""
    # TODO: Get user from session token
    # This is a stub
    return {
        "id": 1,
        "strava_athlete_id": 12345678,
        "firstname": "Ryan",
        "lastname": "Riegel",
        "username": "ryan_riegel",
        "profile_url": "https://...",
        "city": "Glastonbury",
        "state": "Connecticut",
        "country": "United States",
        "default_distance_unit": "metric",
        "preferred_hr_zones": {
            "zone_1": {"min": 0, "max": 115},
            "zone_2": {"min": 115, "max": 135},
            "zone_3": {"min": 135, "max": 155},
            "zone_4": {"min": 155, "max": 175},
            "zone_5": {"min": 175, "max": 220}
        },
        "last_sync_at": "2026-08-15T12:00:00Z",
        "sync_status": "idle",
        "created_at": "2026-01-01T00:00:00Z"
    }

@router.patch("/me")
async def update_user_preferences(db: Session = Depends(get_db)):
    """Update user preferences"""
    # TODO: Update user preferences
    return {"message": "Preferences updated"}

@router.post("/me/sync")
async def trigger_sync(db: Session = Depends(get_db)):
    """Trigger manual sync from Strava"""
    # TODO: Queue background sync job
    return {
        "status": "syncing",
        "message": "Sync started. Check /users/me for progress."
    }
