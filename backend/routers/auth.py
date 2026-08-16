from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from config import settings
import httpx
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()

@router.post("/strava/callback")
async def strava_callback(code: str, db: Session = Depends(get_db)):
    """Handle Strava OAuth callback"""
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/api/v3/oauth/token",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")
        
        token_data = response.json()
    
    # Get athlete profile
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        athlete = response.json()
    
    # Create or update user
    user = db.query(User).filter(User.strava_athlete_id == athlete['id']).first()
    
    if not user:
        user = User(
            strava_athlete_id=athlete['id'],
            firstname=athlete.get('firstname'),
            lastname=athlete.get('lastname'),
            profile_url=athlete.get('profile'),
            city=athlete.get('city'),
            state=athlete.get('state'),
            country=athlete.get('country'),
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_expires_at=datetime.fromtimestamp(token_data['expires_at'])
        )
        db.add(user)
    else:
        user.access_token = token_data['access_token']
        user.refresh_token = token_data['refresh_token']
        user.token_expires_at = datetime.fromtimestamp(token_data['expires_at'])
    
    db.commit()
    db.refresh(user)
    
    # Generate session token (simplified - use JWT in production)
    session_token = f"session_{user.id}_{datetime.now().timestamp()}"
    
    return {
        "user": {
            "id": user.id,
            "strava_athlete_id": user.strava_athlete_id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "profile_url": user.profile_url
        },
        "access_token": session_token,
        "token_type": "Bearer",
        "expires_in": 86400
    }

@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Refresh session token"""
    # TODO: Validate session token and refresh
    return {"access_token": "new_token", "token_type": "Bearer", "expires_in": 86400}

@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout and invalidate session"""
    # TODO: Invalidate session token
    return {"message": "Logged out"}
