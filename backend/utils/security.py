"""Security utilities: password hashing, JWT access tokens, refresh tokens.

Token model (spec v2):
- Access token: short-lived JWT (HS256) carrying sub, exp, iat, tv (token_version).
  Verified statelessly on every request; users.token_version acts as a kill switch.
- Refresh token: opaque random string, stored hashed (SHA-256) in refresh_tokens.
  Rotated on every refresh; replay of a revoked token revokes all user tokens.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "tv": token_version,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """Return the decoded payload, or None on bad signature / expiry / malformed."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def create_refresh_token() -> str:
    """Opaque random token (>=32 bytes of entropy). Only the hash is persisted."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 of the token — the token is the secret, never store it plaintext."""
    return hashlib.sha256(token.encode()).hexdigest()
