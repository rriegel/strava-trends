"""
Tests for the Garmin Personal API client (auth + transport + FIT extraction).
External calls are mocked — no network in tests.
"""
import io
import time
import zipfile
from datetime import date

import httpx
import pytest

import services.garmin_client as gc
from services.garmin_client import (
    GarminApiError,
    GarminClient,
    GarminKeyError,
    assert_key_usable,
    parse_key_expiry,
)


@pytest.fixture(autouse=True)
def _reset_token_cache():
    gc._token_cache.clear()
    yield
    gc._token_cache.clear()


@pytest.fixture
def configure_key(monkeypatch):
    def _set(key="test-api-key", expires="2099-01-01"):
        monkeypatch.setattr(gc.settings, "garmin_api_key", key)
        monkeypatch.setattr(gc.settings, "garmin_api_key_expires_at", expires)
    return _set


def _mock_transport(handler):
    return httpx.AsyncClient(
        base_url=gc.PERSONAL_API_BASE, transport=httpx.MockTransport(handler)
    )


class TestKeyExpiry:
    def test_parse_key_expiry_formats(self):
        assert parse_key_expiry("2099-01-01") == date(2099, 1, 1)
        assert parse_key_expiry("2099-01-01T00:00:00") == date(2099, 1, 1)
        # US format (Garmin settings UI) + whitespace/quotes tolerance
        assert parse_key_expiry("01/15/2099") == date(2099, 1, 15)
        assert parse_key_expiry(' "01/15/2099" ') == date(2099, 1, 15)
        # month/day order: 01 must land in the month slot, not the day slot
        parsed = parse_key_expiry("01/15/2099")
        assert parsed is not None and parsed.month == 1 and parsed.day == 15
        assert parse_key_expiry("") is None
        assert parse_key_expiry("garbage") is None

    def test_missing_key_raises_loudly(self, configure_key, monkeypatch):
        configure_key(key="")
        with pytest.raises(GarminKeyError, match="not configured"):
            assert_key_usable()

    def test_expired_key_raises_loudly(self, configure_key):
        configure_key(expires="2020-01-01")
        with pytest.raises(GarminKeyError, match="EXPIRED"):
            assert_key_usable()

    def test_valid_key_returns_expiry(self, configure_key):
        configure_key(expires="2099-01-01")
        assert assert_key_usable() == date(2099, 1, 1)

    def test_unknown_expiry_still_ok(self, configure_key):
        configure_key(expires="")
        assert assert_key_usable() is None


@pytest.mark.asyncio
class TestTokenLifecycle:
    async def test_mint_and_cache(self, configure_key):
        configure_key()
        mints = []

        async def handler(request):
            if request.url.path == gc.TOKEN_MINT_PATH:
                assert request.headers["Authorization"] == "ApiKey test-api-key"
                mints.append(1)
                return httpx.Response(200, text="tok-1", headers={"content-type": "text/plain"})
            assert request.headers["Authorization"] == "Bearer tok-1"
            return httpx.Response(200, json=[])

        client = GarminClient(http_client=await _mock_transport(handler).__anext__() if False else None)
        # Use a direct client instance with mock transport
        import httpx as _hx

        client = GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )
        await client.list_activities()
        assert len(mints) == 1

        # Second call within TTL must NOT re-mint
        await client.list_activities()
        assert len(mints) == 1
        await client.close()

    async def test_re_mint_on_401(self, configure_key):
        configure_key()
        mints = []

        async def handler(request):
            if request.url.path == gc.TOKEN_MINT_PATH:
                mints.append(1)
                n = len(mints)
                return httpx.Response(200, text=f"tok-{n}", headers={"content-type": "text/plain"})
            if request.headers["Authorization"].endswith("tok-1"):
                return httpx.Response(401)
            return httpx.Response(200, json=[])

        import httpx as _hx

        client = GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )
        result = await client.list_activities()
        assert len(mints) == 2  # minted, 401'd, re-minted once
        assert result == []
        await client.close()

    async def test_mint_failure_raises(self, configure_key):
        configure_key(key="bad-key")

        async def handler(request):
            if request.url.path == gc.TOKEN_MINT_PATH:
                return httpx.Response(403)
            return httpx.Response(200, json=[])

        import httpx as _hx

        client = GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )
        with pytest.raises(GarminApiError, match="Token mint failed"):
            await client.list_activities()
        await client.close()


@pytest.mark.asyncio
class TestListActivities:
    async def _client(self, pages):
        import httpx as _hx

        async def handler(request):
            if request.url.path == gc.TOKEN_MINT_PATH:
                return httpx.Response(200, text="tok-1", headers={"content-type": "text/plain"})
            start = int(request.url.params["start"])
            return httpx.Response(200, json=pages[start])

        return GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )

    async def test_single_page(self, configure_key):
        configure_key()
        client = await self._client(
            {0: [{"activityId": 1, "activityName": "Morning Run"}]}
        )
        result = await client.list_activities()
        assert len(result) == 1
        assert result[0]["activityName"] == "Morning Run"
        await client.close()

    async def test_pagination_follows_until_short_page(self, configure_key):
        configure_key()
        page_a = [{"activityId": i} for i in range(100)]
        page_b = [{"activityId": i} for i in range(100, 150)]
        client = await self._client({0: page_a, 100: page_b})
        result = await client.list_activities()
        assert len(result) == 150
        await client.close()

    async def test_limit_caps_results(self, configure_key):
        configure_key()
        page_a = [{"activityId": i} for i in range(100)]
        client = await self._client({0: page_a})
        result = await client.list_activities(limit=5)
        assert len(result) == 5
        await client.close()

    async def test_error_raises(self, configure_key):
        configure_key()

        async def handler(request):
            if request.url.path == gc.TOKEN_MINT_PATH:
                return httpx.Response(200, text="tok-1", headers={"content-type": "text/plain"})
            return httpx.Response(500)

        import httpx as _hx

        client = GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )
        with pytest.raises(GarminApiError, match="List activities failed"):
            await client.list_activities()
        await client.close()


class TestFitExtraction:
    FIT_BYTES = b"\x0e" + b".FIT" + b"rest-of-file"
    def test_raw_fit_passthrough(self):
        assert (
            GarminClient._extract_fit_bytes(self.FIT_BYTES, "application/octet-stream", "")
            == self.FIT_BYTES
        )

    def test_zip_containing_fit(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("ACTIVITY1.fit", self.FIT_BYTES)
            zf.writestr("readme.txt", "ignore me")
        extracted = GarminClient._extract_fit_bytes(
            buf.getvalue(), "application/zip", ""
        )
        assert extracted == self.FIT_BYTES

    def test_zip_without_fit_raises(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "nothing here")
        with pytest.raises(GarminApiError, match="no .fit file"):
            GarminClient._extract_fit_bytes(buf.getvalue(), "application/zip", "")

    def test_garbage_payload_raises(self):
        with pytest.raises(GarminApiError, match="neither raw FIT nor zip"):
            GarminClient._extract_fit_bytes(b"<html>error</html>", "text/html", "")


@pytest.mark.asyncio
class TestFitCache:
    FIT_BYTES = b"\x0e" + b".FIT" + b"rest-of-file"

    async def test_cache_hit_skips_network(self, tmp_path, configure_key):
        configure_key()
        cache_dir = str(tmp_path / "cache")

        async def handler(request):  # pragma: no cover — must not be reached
            raise AssertionError("network call made despite cache hit")

        import httpx as _hx

        client = GarminClient(
            http_client=_hx.AsyncClient(
                base_url=gc.PERSONAL_API_BASE, transport=_hx.MockTransport(handler)
            )
        )
        # Seed cache directly
        path = client._cache_path(cache_dir, "42")
        import os

        os.makedirs(cache_dir, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.FIT_BYTES)

        data = await client.download_original_fit("42", cache_dir=cache_dir)
        assert data == self.FIT_BYTES
        await client.close()

    async def test_cache_write_atomic(self, tmp_path):
        cache_dir = str(tmp_path / "cache")
        client = GarminClient()
        client._write_cache(cache_dir, "42", self.FIT_BYTES)
        with open(client._cache_path(cache_dir, "42"), "rb") as f:
            assert f.read() == self.FIT_BYTES
        assert not os_path_exists(client._cache_path(cache_dir, "42") + ".tmp")

        # overwrite path (no leftover tmp)
        client._write_cache(cache_dir, "42", b"updated")
        with open(client._cache_path(cache_dir, "42"), "rb") as f:
            assert f.read() == b"updated"
        assert not os_path_exists(client._cache_path(cache_dir, "42") + ".tmp")


def os_path_exists(path):
    import os

    return os.path.exists(path)
