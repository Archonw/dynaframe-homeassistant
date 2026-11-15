"""Small async client for the Dynaframe web API."""

from __future__ import annotations

import asyncio
import hashlib
import ssl
import time
from typing import Any

import aiohttp
from urllib.parse import quote

TIMEOUT = aiohttp.ClientTimeout(total=10)
# The frame builds a mixed playlist synchronously; ~8000 items took 80 s.
PLAY_TIMEOUT = aiohttp.ClientTimeout(total=300)


def _size(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return str(value)


class DynaframeError(Exception):
    """Raised when the frame cannot be reached or answers with an error."""


# Fields of the full settings form that must be sent back unchanged.
SLIDESHOW_FORM_KEYS = (
    "durationSeconds",
    "randomizeOrder",
    "playbackOrderMode",
    "overlaysEnabled",
    "ytDlpEnabled",
    "streamLoadingTransition",
)


class DynaframeAuthError(DynaframeError):
    """The frame asks for a login: API key missing, wrong or sent over http."""


class DynaframeCertError(DynaframeError):
    """The frame's HTTPS certificate is not the one that was pinned."""


def _split_host(host: str) -> tuple[str, int | None]:
    if host.startswith("["):
        name, _, rest = host[1:].partition("]")
        return name, int(rest[1:]) if rest.startswith(":") else None
    if host.count(":") == 1:
        name, port = host.split(":")
        return name, int(port)
    return host, None


async def fetch_fingerprint(host: str) -> str:
    """SHA-256 of the certificate the frame presents on HTTPS, to pin it."""
    name, port = _split_host(host)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(name, port or 443, ssl=context), 10
        )
    except (OSError, asyncio.TimeoutError) as err:
        raise DynaframeError(f"https://{host}: {err}") from err
    try:
        der = writer.get_extra_info("ssl_object").getpeercert(binary_form=True)
    finally:
        writer.close()
    return hashlib.sha256(der).hexdigest()


class MissingSlideshowSettings(DynaframeError):
    """The slideshow settings read lacks fields the settings form needs."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"slideshow settings missing: {', '.join(missing)}")
        self.missing = missing


class DynaframeApi:
    """Wrapper around the HTTP endpoints used by the Dynaframe web UI."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        api_key: str | None = None,
        use_https: bool = False,
        fingerprint: str | None = None,
    ) -> None:
        self._session = session
        self.host = host
        self.use_https = use_https
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        # A pinned certificate replaces the CA check: the frame signs its own.
        self._ssl: Any = None
        if use_https:
            self.set_fingerprint(fingerprint)

    def set_fingerprint(self, fingerprint: str | None) -> None:
        """Pin another certificate (after the frame got a new one)."""
        self._ssl = aiohttp.Fingerprint(bytes.fromhex(fingerprint)) if fingerprint else False

    @property
    def base_url(self) -> str:
        return f"{'https' if self.use_https else 'http'}://{self.host}"

    async def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        raw: bool = False,
        data: dict[str, str] | None = None,
        timeout: aiohttp.ClientTimeout = TIMEOUT,
    ) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                data=data,
                timeout=timeout,
                headers=self._headers,
                ssl=self._ssl,
                allow_redirects=False,
            ) as resp:
                # Web Login answers 401 to a bad key and sends browsers
                # (no key) to its login page. DynaFrame's own login (2026.11.14+)
                # answers 401 over HTTPS and, over plain http, sends everything
                # except a few guest pages to /Connect or refuses it (403).
                location = resp.headers.get("Location", "")
                if resp.status == 401 or (
                    300 <= resp.status < 400 and ("/dfr-login" in location or "/Connect" in location)
                ) or (resp.status == 403 and not self.use_https):
                    raise DynaframeAuthError(f"{method} {path}: login required (HTTP {resp.status})")
                resp.raise_for_status()
                if raw:
                    return await resp.read(), resp.content_type
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except aiohttp.ServerFingerprintMismatch as err:
            raise DynaframeCertError(f"{method} {path}: certificate changed") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DynaframeError(f"{method} {path}: {err}") from err

    # --- read -------------------------------------------------------------
    # Everything goes to the Engine through the web page's /engine-proxy/. That
    # works with and without DynaFrame's own login; with the login on, a
    # "Full REST" API key is accepted only there (and only over HTTPS).
    async def _engine(self, method: str, path: str, **kwargs: Any) -> Any:
        return await self._request(method, f"/engine-proxy{path}", **kwargs)

    async def get_sync_status(self) -> dict[str, Any]:
        return await self._engine("GET", "/sync/status")

    async def get_status(self) -> dict[str, Any]:
        return await self._engine("GET", "/slideshow/status")

    async def get_display_power(self) -> dict[str, Any]:
        # Some displays do not report their power state; the Engine then
        # answers with an error. That must not take the whole frame offline.
        try:
            data = await self._engine("GET", "/display/power")
        except DynaframeAuthError:
            raise
        except DynaframeError:
            return {}
        return data if isinstance(data, dict) and data.get("success") is not False else {}

    async def get_volume(self) -> dict[str, Any]:
        return await self._engine("GET", "/api/v1/system/volume")

    async def get_slideshow_settings(self) -> dict[str, Any]:
        return await self._engine("GET", "/settings/slideshow")

    async def get_playlists(self) -> list[dict[str, Any]]:
        return await self._engine("GET", "/playlists")

    async def get_playback_selection(self) -> dict[str, Any]:
        return await self._engine("GET", "/playback-selection/state")

    async def get_update_status(self) -> dict[str, Any]:
        data = await self._engine("GET", "/api/v1/system/update-presence/status")
        return data.get("status") or {}

    async def get_preview(self, key: str) -> tuple[bytes, str]:
        # Only the web page makes previews; with DynaFrame's login on it does
        # not accept API keys, so the picture is then missing (no error).
        return await self._request(
            "GET",
            f"/Home/CaptureRendererPreview?v={key}&t={int(time.time() * 1000)}",
            raw=True,
        )

    # --- control ----------------------------------------------------------
    async def next(self) -> None:
        await self._engine("POST", "/slideshow/next")

    async def previous(self) -> None:
        await self._engine("POST", "/slideshow/previous")

    async def pause(self) -> None:
        await self._engine("POST", "/slideshow/pause")

    async def resume(self) -> None:
        await self._engine("POST", "/slideshow/resume")

    async def stop(self) -> None:
        await self._engine("POST", "/slideshow/stop")

    async def set_display_power(self, on: bool) -> None:
        await self._request(
            "POST", "/engine-proxy/display/power", json={"state": "on" if on else "off"}
        )

    async def set_volume(self, value: int) -> None:
        await self._engine("POST", "/api/v1/system/volume", json={"value": value})

    async def set_mute(self, muted: bool) -> None:
        await self._engine("POST", "/api/v1/system/mute", json={"muted": muted})

    async def update_slideshow_settings(self, **settings: Any) -> None:
        await self._engine("POST", "/settings/slideshow", json=settings)

    async def get_transition_settings(self, name: str) -> dict[str, Any]:
        return await self._engine("GET", f"/renderer/shaders/{quote(name, safe='')}/settings")

    async def get_transition_metadata(self, name: str) -> dict[str, Any]:
        return await self._engine("GET", f"/renderer/shaders/{quote(name, safe='')}/metadata")

    async def set_transition(self, name: str) -> None:
        # Also stored as the default transition (settings/slideshow).
        await self._engine("POST", "/transition", json={"transition": name})

    async def set_transition_settings(self, name: str, settings: dict[str, Any]) -> None:
        await self._engine(
            "POST", f"/renderer/shaders/{quote(name, safe='')}/settings", json=settings
        )

    async def list_overlays(self) -> list[dict[str, Any]]:
        return await self._engine("GET", "/overlay/list")

    async def set_overlays_enabled(self, enabled: bool) -> None:
        await self._engine("POST", "/settings/slideshow", json={"overlaysEnabled": enabled})

    async def set_default_overlay(self, file_name: str, slideshow: dict[str, Any]) -> None:
        """Set the default overlay (the Engine takes single settings)."""
        await self._engine("POST", "/settings/slideshow", json={"defaultOverlay": file_name})

    async def get_memory(self) -> dict[str, Any]:
        info = await self._engine("GET", "/system/info")
        memory = (info or {}).get("memory") or {}
        total, available = memory.get("total"), memory.get("available")
        if not total or available is None:
            return {}
        return {
            "percentUsed": round((total - available) * 100 / total, 1),
            "totalFormatted": _size(total),
            "availableFormatted": _size(available),
        }

    async def get_disks(self) -> list[dict[str, Any]]:
        return await self._engine("GET", "/system/diskspace")

    async def reboot(self) -> None:
        await self._engine("POST", "/api/v1/system/power/restart-system")

    async def play_playlists(self, playlist_ids: list[int], name: str) -> None:
        await self._request(
            "POST",
            "/engine-proxy/playlists/play-selection",
            timeout=PLAY_TIMEOUT,
            json={
                "startPlayback": True,
                "playlistName": name,
                "quickMixState": {
                    "selectedFolders": [],
                    "selectedPlugins": [],
                    "enabledSavedPlaylistIds": playlist_ids,
                },
            },
        )
