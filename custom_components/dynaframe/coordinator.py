"""Polling coordinator for a single Dynaframe."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DynaframeApi, DynaframeError
from .const import DOMAIN, SCAN_INTERVAL, SLOW_POLL_EVERY

_LOGGER = logging.getLogger(__name__)


def is_user_playlist(playlist: dict[str, Any]) -> bool:
    """Hide the runtime "quick mix" playlists the frame creates itself."""
    return '"quick_mix"' not in (playlist.get("description") or "")


@dataclass
class DynaframeData:
    status: dict[str, Any] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)
    volume: dict[str, Any] = field(default_factory=dict)
    slideshow: dict[str, Any] = field(default_factory=dict)
    selection: dict[str, Any] = field(default_factory=dict)
    playlists: list[dict[str, Any]] = field(default_factory=list)
    update: dict[str, Any] = field(default_factory=dict)
    peers: list[dict[str, Any]] = field(default_factory=list)
    sync: dict[str, Any] = field(default_factory=dict)
    overlays: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    disks: list[dict[str, Any]] = field(default_factory=list)
    transition_settings: dict[str, Any] = field(default_factory=dict)
    transition_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def transition(self) -> str | None:
        return self.slideshow.get("defaultTransition")

    @property
    def transition_duration(self) -> float | None:
        """Saved duration, else the effect's default (seconds)."""
        if "duration" in self.transition_settings:
            return self.transition_settings["duration"]
        for setting in self.transition_metadata.get("settings") or []:
            if setting.get("key") == "duration":
                return setting.get("default")
        return None

    @property
    def user_playlists(self) -> list[dict[str, Any]]:
        return [p for p in self.playlists if is_user_playlist(p)]

    @property
    def active_playlists(self) -> list[dict[str, Any]]:
        """Saved playlists the frame is currently mixing (one or more)."""
        ids = (self.selection.get("quickMixState") or {}).get(
            "enabledSavedPlaylistIds"
        ) or []
        if self.selection.get("savedPlaylistId"):
            ids = [self.selection["savedPlaylistId"]]
        by_id = {p.get("id"): p for p in self.playlists}
        return [by_id[i] for i in ids if i in by_id]

    @property
    def current_playlist(self) -> dict[str, Any] | None:
        active = self.active_playlists
        return active[0] if len(active) == 1 else None

    @property
    def display_on(self) -> bool:
        return self.display.get("state") == "on" and not self.status.get("isSleeping")


class DynaframeCoordinator(DataUpdateCoordinator[DynaframeData]):
    """Fetches all frame state in one go."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: DynaframeApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self._polls = 0
        self._metadata: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> DynaframeData:
        previous = self.data or DynaframeData()
        slow = self._polls % SLOW_POLL_EVERY == 0
        self._polls += 1
        try:
            data = DynaframeData(
                status=await self.api.get_status(),
                display=await self.api.get_display_power(),
                volume=await self.api.get_volume(),
                slideshow=await self.api.get_slideshow_settings(),
                selection=await self.api.get_playback_selection(),
                playlists=await self.api.get_playlists() if slow else previous.playlists,
                update=await self.api.get_update_status() if slow else previous.update,
                sync=await self.api.get_sync_status() if slow else previous.sync,
                overlays=await self.api.list_overlays() if slow else previous.overlays,
                memory=await self.api.get_memory() if slow else previous.memory,
                disks=await self.api.get_disks() if slow else previous.disks,
            )
            data.peers = data.sync.get("discoveredFrames") or []
            if name := data.transition:
                if name not in self._metadata:
                    self._metadata[name] = await self.api.get_transition_metadata(name)
                data.transition_metadata = self._metadata[name]
                data.transition_settings = await self.api.get_transition_settings(name)
        except DynaframeError as err:
            self._polls = 0  # refresh everything once the frame is back
            raise UpdateFailed(str(err)) from err
        return data

    async def async_refresh_playlists(self) -> None:
        """Force the slow data to be refreshed with the next poll."""
        self._polls = 0
        await self.async_request_refresh()
