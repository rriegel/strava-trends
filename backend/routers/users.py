from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from routers.auth import get_current_user

router = APIRouter()

class UserPreferencesUpdate(BaseModel):
    max_hr: Optional[int] = None
    default_distance_unit: Optional[str] = None

@router.get("/me")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    return {
        "id": current_user.id,
        "strava_athlete_id": current_user.strava_athlete_id,
        "firstname": current_user.firstname,
        "lastname": current_user.lastname,
        "username": current_user.username,
        "profile_url": current_user.profile_url,
        "city": current_user.city,
        "state": current_user.state,
        "country": current_user.country,
        "default_distance_unit": current_user.default_distance_unit,
        "preferred_hr_zones": current_user.preferred_hr_zones,
        "max_hr": current_user.max_hr,
        "last_sync_at": current_user.last_sync_at.isoformat() if current_user.last_sync_at else None,
        "sync_status": current_user.sync_status,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.patch("/me")
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    if preferences.max_hr is not None:
        # Validate max_hr is reasonable (30-250 bpm)
        if preferences.max_hr < 30 or preferences.max_hr > 250:
            raise HTTPException(status_code=400, detail="max_hr must be between 30 and 250 bpm")
        current_user.max_hr = preferences.max_hr
    
    if preferences.default_distance_unit is not None:
        if preferences.default_distance_unit not in ['metric', 'imperial']:
            raise HTTPException(status_code=400, detail="default_distance_unit must be 'metric' or 'imperial'")
        current_user.default_distance_unit = preferences.default_distance_unit
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Preferences updated",
        "max_hr": current_user.max_hr,
        "default_distance_unit": current_user.default_distance_unit
    }

@router.post("/me/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger manual sync from Strava"""
    # TODO: Queue background sync job
    return {
        "status": "syncing",
        "message": "Sync started. Check /users/me for progress."
    }
