"""
Garmin Personal API client.

Handles auth (API key -> 24h OAuth2 token, re-minted on 401 — Garmin's Personal
API has no refresh tokens) and the transport calls the sync service needs:
list activities, download the original FIT file, fetch activity detail.

Auth mechanics (verified from Garmin developer docs, 2026-11-04 — see vault
Projects/garmin-personal-api-research.md):
  POST /personalapitoken-service/personal-api/personal-api-key/token
      Authorization: ApiKey <key>  ->  {"access_token": "...", "expires_in": 86400}
  Personal API base: https://personal.connectapi.garmin.com
"""
import asyncio
import os
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from config import settings

PERSONAL_API_BASE = "https://personal.connectapi.garmin.com"
TOKEN_MINT_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"

# Conservative default pacing for the download loop (rate limits are not
# documented for the Personal tier — verify empirically; back off on 429).
DEFAULT_REQUEST_PACE_SECONDS = 1.0

# Re-mint slightly before the documented 24h expiry.
TOKEN_CACHE_SECONDS = 23 * 3600


class GarminKeyError(Exception):
    """Garmin API key missing, expired, or within the expiry-warning window."""


class GarminApiError(Exception):
    """Garmin Personal API returned an unexpected/failed response."""


class _TokenCache:
    """In-process token cache with a monotonic-clock TTL."""

    def __init__(self):
        self._token: Optional[str] = None
        self._expires_monotonic: float = 0.0

    def get(self) -> Optional[str]:
        if self._token and time.monotonic() < self._expires_monotonic:
            return self._token
        return None

    def put(self, token: str) -> None:
        self._token = token
        self._expires_monotonic = time.monotonic() + TOKEN_CACHE_SECONDS

    def clear(self) -> None:
        self._token = None
        self._expires_monotonic = 0.0


_token_cache = _TokenCache()


def parse_key_expiry(raw: str) -> Optional[date]:
    """
    Parse GARMIN_API_KEY_EXPIRES_AT -> date, or None if unset/unparseable.

    Accepts ISO (YYYY-MM-DD, the documented format) and US (MM/DD/YYYY —
    the format Garmin's Connect settings UI displays) plus optional
    surrounding whitespace/quotes. Unparseable values return None (unknown
    expiry) rather than raising so a typo never blocks syncs; the status
    endpoint surfaces the unknown state.
    """
    raw = (raw or "").strip().strip('"').strip("'")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    # US format MM/DD/YYYY (Garmin settings UI shows this)
    try:
        month, day, year = raw[:10].split("/")
        return date(int(year), int(month), int(day))
    except (ValueError, TypeError):
        return None


def assert_key_usable() -> Optional[date]:
    """
    Fail LOUDLY when the key is missing or expired. Also warn (but still allow)
    when within 7 days of expiry — Garmin emails ~1 week ahead.

    Returns the parsed expiry date (or None if unknown) for the status endpoint.
    """
    if not settings.garmin_api_key:
        raise GarminKeyError(
            "Garmin Personal API key is not configured. Create one in Garmin "
            "Connect Web -> Settings -> Personal API Key and set GARMIN_API_KEY "
            "in backend/.env (the key is shown only once at creation)."
        )
    expiry = parse_key_expiry(settings.garmin_api_key_expires_at)
    if expiry:
        days_left = (expiry - date.today()).days
        if days_left < 0:
            raise GarminKeyError(
                f"Garmin API key EXPIRED on {expiry.isoformat()}. Create a new "
                "key in Garmin Connect Web -> Settings -> Personal API Key and "
                "update GARMIN_API_KEY in backend/.env."
            )
    return expiry


class GarminClient:
    """
    Thin async client for the Garmin Personal API.

    Token lifecycle: mint with the API key, cache ~23h, transparently re-mint
    once (cache clear) on a 401 before surfacing the failure.
    """

    def __init__(
        self,
        request_pace_seconds: float = DEFAULT_REQUEST_PACE_SECONDS,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._pace = request_pace_seconds
        self._client = http_client  # injectable for tests

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=PERSONAL_API_BASE, timeout=60.0
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _mint_token(self) -> str:
        client = await self._http()
        response = await client.post(
            TOKEN_MINT_PATH,
            headers={"Authorization": f"ApiKey {settings.garmin_api_key}"},
        )
        if response.status_code != 200:
            raise GarminApiError(
                f"Token mint failed ({response.status_code}). Check the API key "
                "and its expiry."
            )
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise GarminApiError("Token mint response missing access_token")
        _token_cache.put(token)
        return token

    async def _auth_header(self) -> Dict[str, str]:
        token = _token_cache.get()
        if not token:
            token = await self._mint_token()
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        allow_retry: bool = True,
    ) -> httpx.Response:
        """Authenticated request with 429 backoff and one transparent re-mint on 401."""
        client = await self._http()
        headers = await self._auth_header()

        backoff = 2.0
        while True:
            response = await client.request(
                method, path, params=params, headers=headers
            )

            if response.status_code == 401 and allow_retry:
                # Token expired mid-window (or revoked): clear cache, re-mint once.
                _token_cache.clear()
                headers = await self._auth_header()
                allow_retry = False
                continue

            if response.status_code == 429:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
                continue

            return response

    async def list_activities(
        self,
        *,
        start_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:
        """
        List activities (newest first, Garmin's default ordering), following
        pagination until exhausted (or `limit` collected).

        Returns the raw summary dicts. Note: Garmin's list payload carries
        startTimeLocal (timezone-naive); callers needing UTC should prefer the
        beginTimestamp epoch millis field when present.
        """
        activities: list[Dict[str, Any]] = []
        start = 0
        page_size = 100
        while True:
            params: Dict[str, Any] = {"start": start, "limit": page_size}
            if start_date:
                params["startdate"] = start_date.isoformat()
            response = await self._request(
                "GET",
                "/activitylist-service/activities/search/activities",
                params=params,
            )
            if response.status_code != 200:
                raise GarminApiError(
                    f"List activities failed ({response.status_code})"
                )
            page = response.json()
            if not page:
                break
            activities.extend(page)
            if limit and len(activities) >= limit:
                return activities[:limit]
            if len(page) < page_size:
                break
            start += page_size
            await asyncio.sleep(self._pace)
        return activities

    async def get_activity_detail(self, activity_id: str) -> Dict[str, Any]:
        response = await self._request(
            "GET", f"/activity-service/activity/{activity_id}"
        )
        if response.status_code != 200:
            raise GarminApiError(
                f"Activity detail failed for {activity_id} "
                f"({response.status_code})"
            )
        return response.json()

    async def download_original_fit(
        self, activity_id: str, cache_dir: Optional[str] = None
    ) -> bytes:
        """
        Download the ORIGINAL activity file (FIT) for an activity.

        The endpoint may return the raw .FIT bytes directly or a zip archive
        containing the file(s) — verify empirically on first sync; both shapes
        are handled here.

        When `cache_dir` is set, a previously-downloaded file for this activity
        is returned from disk without a network call (re-syncs never re-download).
        """
        if cache_dir:
            cached = self._read_cache(cache_dir, activity_id)
            if cached is not None:
                return cached

        response = await self._request(
            "GET", f"/download-service/files/activity/{activity_id}"
        )
        if response.status_code != 200:
            raise GarminApiError(
                f"FIT download failed for {activity_id} ({response.status_code})"
            )

        content = self._extract_fit_bytes(
            response.content,
            content_type=response.headers.get("content-type", ""),
            url_filename=response.headers.get("content-disposition", ""),
        )

        if cache_dir:
            self._write_cache(cache_dir, activity_id, content)
        return content

    @staticmethod
    def _extract_fit_bytes(
        content: bytes, content_type: str, url_filename: str
    ) -> bytes:
        """Handle raw-FIT vs zip-wrapped responses defensively."""
        if "zip" in content_type.lower() or content[:2] == b"PK":
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                fit_names = [
                    n for n in zf.namelist() if n.lower().endswith(".fit")
                ]
                if not fit_names:
                    raise GarminApiError(
                        "Download archive contained no .fit file: "
                        f"{zf.namelist()}"
                    )
                return zf.read(fit_names[0])

        if not content.startswith(b"\x0e"):  # FIT files begin with a header: length byte + '.FIT'
            header_magic = content[4:8]
            if header_magic != b".FIT":
                raise GarminApiError(
                    "Download payload is neither raw FIT nor zip "
                    f"(content-type={content_type!r}, first bytes={content[:8]!r})"
                )
        return content

    @staticmethod
    def _cache_path(cache_dir: str, activity_id: str) -> str:
        return os.path.join(cache_dir, f"{activity_id}.fit")

    def _read_cache(self, cache_dir: str, activity_id: str) -> Optional[bytes]:
        path = self._cache_path(cache_dir, activity_id)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def _write_cache(self, cache_dir: str, activity_id: str, content: bytes) -> None:
        os.makedirs(cache_dir, exist_ok=True)
        tmp_path = self._cache_path(cache_dir, activity_id) + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(content)
        os.replace(tmp_path, self._cache_path(cache_dir, activity_id))

    async def pace_sleep(self) -> None:
        """Inter-request pacing hook (between downloads)."""
        await asyncio.sleep(self._pace)
