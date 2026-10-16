"""Small async client for the Dynaframe web API."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=10)


class DynaframeError(Exception):
    """Raised when the frame cannot be reached or answers with an error."""


class DynaframeApi:
    """Wrapper around the HTTP endpoints used by the Dynaframe web UI."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host

    @property
    def base_url(self) -> str:
        return f"http://{self.host}"

    async def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        raw: bool = False,
        data: dict[str, str] | None = None,
    ) -> Any:
        try:
            async with self._session.request(
                method, f"{self.base_url}{path}", json=json, data=data, timeout=TIMEOUT
            ) as resp:
                resp.raise_for_status()
                if raw:
                    return await resp.read(), resp.content_type
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DynaframeError(f"{method} {path}: {err}") from err

    # --- read -------------------------------------------------------------
    async def get_sync_status(self) -> dict[str, Any]:
        return await self._request("GET", "/Sync/GetSyncStatus")

    async def get_status(self) -> dict[str, Any]:
        return await self._request("GET", "/Home/GetStatus")

    async def get_display_power(self) -> dict[str, Any]:
        return await self._request("GET", "/Home/GetDisplayPower")

    async def get_volume(self) -> dict[str, Any]:
        return await self._request("GET", "/Settings/GetAudioVolume")

    async def get_slideshow_settings(self) -> dict[str, Any]:
        return await self._request("GET", "/Home/GetSlideshowSettings")

    async def get_playlists(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/engine-proxy/playlists")

    async def get_playback_selection(self) -> dict[str, Any]:
        return await self._request("GET", "/engine-proxy/playback-selection/state")

    async def get_update_status(self) -> dict[str, Any]:
        data = await self._request("GET", "/Update/PresenceStatus")
        return data.get("status") or {}

    async def get_preview(self, key: str) -> tuple[bytes, str]:
        return await self._request(
            "GET",
            f"/Home/CaptureRendererPreview?v={key}&t={int(time.time() * 1000)}",
            raw=True,
        )

    # --- control ----------------------------------------------------------
    async def next(self) -> None:
        await self._request("POST", "/Home/Next")

    async def previous(self) -> None:
        await self._request("POST", "/Home/Previous")

    async def pause(self) -> None:
        await self._request("POST", "/Home/Pause")

    async def resume(self) -> None:
        await self._request("POST", "/Home/Resume")

    async def stop(self) -> None:
        await self._request("POST", "/engine-proxy/slideshow/stop")

    async def set_display_power(self, on: bool) -> None:
        await self._request(
            "POST", "/Home/SetDisplayPower", json={"state": "on" if on else "off"}
        )

    async def set_volume(self, value: int) -> None:
        await self._request("POST", "/Settings/SetAudioVolume", json={"value": value})

    async def set_mute(self, muted: bool) -> None:
        await self._request("POST", "/Settings/SetAudioMute", json={"value": muted})

    async def update_slideshow_settings(self, **settings: Any) -> None:
        await self._request("POST", "/Home/UpdateSlideshowSettings", json=settings)

    async def get_transition_settings(self, name: str) -> dict[str, Any]:
        return await self._request("GET", f"/Settings/GetShaderSettings?shaderName={name}")

    async def get_transition_metadata(self, name: str) -> dict[str, Any]:
        return await self._request("GET", f"/Settings/GetShaderMetadata?shaderName={name}")

    async def set_transition(self, name: str) -> None:
        await self._request("POST", f"/Settings/SetShader?shader={name}")

    async def set_transition_settings(self, name: str, settings: dict[str, Any]) -> None:
        await self._request(
            "POST", f"/Settings/SetShaderSettings?shaderName={name}", json=settings
        )

    async def list_overlays(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/Overlay/ListOverlays")

    async def set_overlays_enabled(self, enabled: bool) -> None:
        await self._request(
            "POST", "/Overlay/SetOverlayMasterSetting", json={"enabled": enabled}
        )

    async def set_default_overlay(self, file_name: str, slideshow: dict[str, Any]) -> None:
        """Only the full settings form accepts the default overlay."""

        def flag(key: str) -> str:
            return "true" if slideshow.get(key) else "false"

        await self._request(
            "POST",
            "/Settings/UpdateSlideshowSettings",
            data={
                "durationSeconds": str(slideshow.get("durationSeconds", 20)),
                "randomizeOrder": flag("randomizeOrder"),
                "playbackOrderMode": slideshow.get("playbackOrderMode", ""),
                "defaultOverlay": file_name,
                "overlaysEnabled": flag("overlaysEnabled"),
                "ytDlpEnabled": flag("ytDlpEnabled"),
                "streamLoadingTransition": flag("streamLoadingTransition"),
            },
        )

    async def get_memory(self) -> dict[str, Any]:
        return await self._request("GET", "/Log/GetMemoryStats")

    async def get_disks(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/engine-proxy/system/diskspace")

    async def reboot(self) -> None:
        await self._request("POST", "/Settings/PowerControl?action=restart-system")

    async def play_playlists(self, playlist_ids: list[int], name: str) -> None:
        await self._request(
            "POST",
            "/engine-proxy/playlists/play-selection",
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
