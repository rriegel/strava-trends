from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.refresh_token import RefreshToken
from config import settings
from utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    hash_refresh_token,
)
import httpx
from datetime import datetime, timedelta, timezone

router = APIRouter()
security = HTTPBearer()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    refresh_token: str


# ---------------------------------------------------------------------------
# Token issuance
# ---------------------------------------------------------------------------

def _issue_tokens(user: User, db: Session) -> TokenResponse:
    """Create an access token + persist a new refresh token row."""
    access = create_access_token(user.id, user.token_version or 0)
    raw = create_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(row)
    db.commit()
    return TokenResponse(
        access_token=access,
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_token=raw,
    )


def _revoke_all_refresh_tokens(user_id: int, db: Session) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(timezone.utc)})


# ---------------------------------------------------------------------------
# get_current_user (rewrite — same name/signature so Depends() keeps working)
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from a JWT access token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    token_version = payload.get("tv")
    if user_id is None or token_version is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    # Kill switch: password change / "log out all devices" bumps token_version
    if (user.token_version or 0) != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked"
        )
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled"
        )
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    username = body.username or body.email.split("@")[0]
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )
    user = User(
        email=body.email,
        username=username,
        password_hash=hash_password(body.password),
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(
        body.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if row.revoked_at is not None:
        # Replay of a revoked token = stolen-token signal → revoke everything
        _revoke_all_refresh_tokens(row.user_id, db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    # Rotate: revoke the old token, issue a fresh pair
    row.revoked_at = datetime.now(timezone.utc)
    # Sweep expired rows (cheap at personal scale; keeps the table small)
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.now(timezone.utc)
    ).delete(synchronize_session=False)
    return _issue_tokens(user, db)


@router.post("/logout")
async def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke the presented refresh token server-side (200 even if already invalid)."""
    token_hash = hash_refresh_token(body.refresh_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Logged out"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.password_hash or not verify_password(
        body.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    current_user.password_hash = hash_password(body.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    _revoke_all_refresh_tokens(current_user.id, db)
    db.commit()
    return _issue_tokens(current_user, db)


@router.post("/strava/callback")
async def strava_callback(code: str, db: Session = Depends(get_db)):
    """Handle Strava OAuth callback — creates/updates user, mints a real token pair."""
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

    return _issue_tokens(user, db)


@router.get("/dev-login")
async def dev_login(db: Session = Depends(get_db)):
    """
    Development login - creates or returns default user (id=1).
    Gated behind settings.dev_login_enabled (default False) — 403 when disabled.
    """
    if not settings.dev_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is disabled",
        )

    # Get or create default user
    user = db.query(User).filter(User.id == 1).first()

    if not user:
        user = User(
            id=1,
            strava_athlete_id=None,  # No Strava integration
            username="default_user",
            firstname="Default",
            lastname="User",
            email=None,
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
            sync_status="idle"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _issue_tokens(user, db)
