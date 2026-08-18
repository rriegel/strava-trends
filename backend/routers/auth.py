from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from config import settings
import httpx
from datetime import datetime, timedelta
import urllib.parse

router = APIRouter()
security = HTTPBearer()


async def refresh_strava_token(user: User, db: Session) -> str:
    """Refresh expired Strava access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/api/v3/oauth/token",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": user.refresh_token,
                "grant_type": "refresh_token"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh Strava token"
            )
        
        token_data = response.json()
    
    # Update user tokens
    user.access_token = token_data['access_token']
    user.refresh_token = token_data['refresh_token']
    user.token_expires_at = datetime.fromtimestamp(token_data['expires_at'])
    db.commit()
    
    return user.access_token

async def get_valid_strava_token(user: User, db: Session) -> str:
    """Get valid Strava access token, refreshing if needed"""
    if datetime.now() >= user.token_expires_at - timedelta(minutes=5):
        return await refresh_strava_token(user, db)
    return user.access_token

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from session token"""
    # TODO: Validate session token properly (JWT in production)
    # For now, extract user_id from token format: session_{user_id}_{timestamp}
    token = credentials.credentials
    
    if not token.startswith("session_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    try:
        parts = token.split("_")
        user_id = int(parts[1])
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except (IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.get("/strava/connect")
async def strava_connect():
    """Generate Strava OAuth authorization URL"""
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "scope": "read,activity:read_all,profile:read_all",
        "approval_prompt": "auto"
    }
    auth_url = f"https://www.strava.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    return {"authorization_url": auth_url}

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
