"""
Auth tests: register, login, refresh (rotation/replay), logout, change-password,
token_version kill switch, and JWT verification. Per two-DB rule, hits 5433.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from utils.security import (
    create_access_token,
    hash_refresh_token,
)


def _register(client: TestClient, email="test@example.com", password="supersecret1"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

def test_register_happy_path(client):
    resp = _register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "Bearer"
    assert body["refresh_token"]
    assert body["expires_in"] > 0


def test_register_duplicate_email(client):
    _register(client, email="dup@example.com")
    resp = _register(client, email="dup@example.com")
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = _register(client, password="short")
    assert resp.status_code == 422


def test_register_invalid_email(client):
    resp = _register(client, email="not-an-email")
    assert resp.status_code == 422


def test_register_disabled(client):
    from config import settings
    with patch.object(settings, "registration_enabled", False):
        resp = _register(client)
    assert resp.status_code == 403


def test_register_username_defaults_to_email_local_part(client):
    resp = _register(client, email="jane@example.com")
    assert resp.status_code == 200
    # verify via /users/me
    me = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {resp.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "jane"


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

def test_login_good_credentials(client):
    _register(client, email="login@example.com", password="supersecret1")
    resp = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["refresh_token"]


def test_login_wrong_password(client):
    _register(client, email="login2@example.com", password="supersecret1")
    resp = client.post(
        "/auth/login",
        json={"email": "login2@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 401


def test_login_no_password_hash(client, sample_user):
    """OAuth-provider-only user (no password_hash) cannot log in with email+password."""
    resp = client.post(
        "/auth/login",
        json={"email": sample_user.email, "password": "whatever"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user / JWT verification
# ---------------------------------------------------------------------------

def test_get_me_with_valid_token(client):
    reg = _register(client)
    me = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "test"  # local-part fallback when username omitted


def test_get_me_with_garbage_token(client):
    resp = client.get(
        "/users/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


def test_get_me_with_expired_token(client, sample_user):
    expired = create_access_token(sample_user.id, sample_user.token_version or 0)
    # Mint with a negative-expiry payload by patching the config window
    from config import settings
    with patch.object(settings, "access_token_expire_minutes", -1):
        expired = create_access_token(sample_user.id, sample_user.token_version or 0)
    resp = client.get(
        "/users/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401


def test_get_me_with_stale_token_version(client, sample_user):
    """Token minted with tv=0 but user bumped to tv=1 → 401."""
    token = create_access_token(sample_user.id, 0)
    sample_user.token_version = 1
    from database import get_db  # fixture session is the same one
    resp = client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------

def test_refresh_rotates(client):
    reg = _register(client)
    old_refresh = reg.json()["refresh_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new = resp.json()
    assert new["refresh_token"] != old_refresh
    assert new["access_token"]


def test_refresh_replay_revokes_all(client):
    reg = _register(client)
    old_refresh = reg.json()["refresh_token"]
    # First refresh: rotates → old token now revoked
    first = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    # Replay of the revoked token → all tokens for the user revoked
    replay = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401
    # The token issued by the first refresh is now also dead
    second_refresh = first.json()["refresh_token"]
    third = client.post("/auth/refresh", json={"refresh_token": second_refresh})
    assert third.status_code == 401


def test_refresh_invalid_token(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "bogus"})
    assert resp.status_code == 401


def test_refresh_expired(client):
    reg = _register(client)
    # Manually expire the row
    from models.refresh_token import RefreshToken
    from database import get_db  # noqa: F401
    # Access the test DB session via the client's dependency override
    from tests.conftest import TestingSessionLocal
    token_hash = hash_refresh_token(reg.json()["refresh_token"])
    db = TestingSessionLocal()
    try:
        row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
    resp = client.post("/auth/refresh", json={"refresh_token": reg.json()["refresh_token"]})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

def test_logout_revokes_refresh_token(client):
    reg = _register(client)
    refresh_token = reg.json()["refresh_token"]
    resp = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    # Refresh with the revoked token → 401
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_logout_idempotent(client):
    reg = _register(client)
    refresh_token = reg.json()["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": refresh_token}).status_code == 200
    assert client.post("/auth/logout", json={"refresh_token": refresh_token}).status_code == 200


# ---------------------------------------------------------------------------
# change-password + token_version kill switch
# ---------------------------------------------------------------------------

def test_change_password_invalidates_access_token(client):
    reg = _register(client)
    old_access = reg.json()["access_token"]
    old_refresh = reg.json()["refresh_token"]
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "supersecret1", "new_password": "newsecret123"},
        headers={"Authorization": f"Bearer {old_access}"},
    )
    assert resp.status_code == 200
    # Old access token is dead (token_version bumped)
    me = client.get(
        "/users/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert me.status_code == 401
    # Old refresh token is dead
    resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401
    # Login with the new password works
    resp = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "newsecret123"},
    )
    assert resp.status_code == 200


def test_change_password_wrong_current(client):
    reg = _register(client)
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "wrongpass", "new_password": "newsecret123"},
        headers={"Authorization": f"Bearer {reg.json()['access_token']}"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# dev-login gate
# ---------------------------------------------------------------------------

def test_dev_login_disabled_by_default(client):
    resp = client.get("/auth/dev-login")
    assert resp.status_code == 403


def test_dev_login_enabled(client):
    from config import settings
    with patch.object(settings, "dev_login_enabled", True):
        resp = client.get("/auth/dev-login")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


# ---------------------------------------------------------------------------
# strava callback (token mint via _issue_tokens)
# ---------------------------------------------------------------------------

def test_strava_callback_mints_tokens(client, mock_strava_api):
    token_data = {
        "access_token": "strava_access",
        "refresh_token": "strava_refresh",
        "expires_at": int((datetime.now() + timedelta(hours=6)).timestamp()),
    }
    athlete = mock_strava_api["athlete"]

    class FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    def fake_post(url, data=None):
        return FakeResponse(token_data)

    def fake_get(url, headers=None):
        return FakeResponse(athlete)

    with patch("routers.auth.httpx.AsyncClient") as fake_client_cls:
        fake_client = fake_client_cls.return_value.__aenter__.return_value
        fake_client.post.side_effect = fake_post
        fake_client.get.side_effect = fake_get

        resp = client.post("/auth/strava/callback?code=abc123")

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    # Access token should be a real JWT now (3 segments), not the forgeable session format
    assert body["access_token"].count(".") == 2
