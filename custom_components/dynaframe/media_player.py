"""Media player entity: the main control surface of a Dynaframe."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DynaframeConfigEntry
from .api import DynaframeError
from .const import DOMAIN
from .entity import DynaframeEntity

# Live content (videos, camera streams) changes without a new item, so the
# preview image is re-captured at most this often.
PREVIEW_REFRESH_SECONDS = 30

FEATURES = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SHUFFLE_SET
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynaframeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([DynaframeMediaPlayer(entry.runtime_data)])
    entity_platform.async_get_current_platform().async_register_entity_service(
        "play_playlists",
        {vol.Required("playlists"): vol.All(cv.ensure_list, [cv.string])},
        "async_play_playlists",
    )


class DynaframeMediaPlayer(DynaframeEntity, MediaPlayerEntity):
    """Slideshow, display power and audio of one frame."""

    _attr_name = None
    _attr_translation_key = "frame"
    _attr_supported_features = FEATURES
    _attr_media_image_remotely_accessible = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "media_player")

    @property
    def _item(self) -> dict[str, Any]:
        return self.coordinator.data.status.get("currentItem") or {}

    @property
    def state(self) -> MediaPlayerState:
        data = self.coordinator.data
        if not data.display_on:
            return MediaPlayerState.OFF
        if not data.status.get("isRunning"):
            return MediaPlayerState.IDLE
        if data.status.get("isPaused"):
            return MediaPlayerState.PAUSED
        return MediaPlayerState.PLAYING

    @property
    def media_title(self) -> str | None:
        return self._item.get("title") or self._item.get("fileName")

    @property
    def media_artist(self) -> str | None:
        return self._item.get("author")

    @property
    def media_album_name(self) -> str | None:
        names = [p["name"] for p in self.coordinator.data.active_playlists]
        return " + ".join(names) if names else None

    @property
    def media_content_id(self) -> str | None:
        item_id = self._item.get("id")
        return str(item_id) if item_id is not None else None

    @property
    def media_content_type(self) -> MediaType | str | None:
        media_type = self._item.get("mediaType")
        if media_type == "video":
            return MediaType.VIDEO
        if media_type:
            return MediaType.IMAGE
        return None

    @property
    def media_image_hash(self) -> str | None:
        if self.state is MediaPlayerState.OFF or not self._item:
            return None
        bucket = int(time.time() // PREVIEW_REFRESH_SECONDS)
        if self._item.get("mediaType") != "video":
            bucket = 0
        return f"{self._item.get('id')}-{bucket}"

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        try:
            return await self.coordinator.api.get_preview(self.media_image_hash or "")
        except DynaframeError:
            return None, None

    @property
    def volume_level(self) -> float | None:
        value = self.coordinator.data.volume.get("value")
        return value / 100 if value is not None else None

    @property
    def is_volume_muted(self) -> bool | None:
        return self.coordinator.data.volume.get("muted")

    @property
    def shuffle(self) -> bool | None:
        return self.coordinator.data.slideshow.get("randomizeOrder")

    @property
    def source_list(self) -> list[str]:
        return [p["name"] for p in self.coordinator.data.user_playlists]

    @property
    def source(self) -> str | None:
        playlist = self.coordinator.data.current_playlist
        return playlist.get("name") if playlist else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Deliberately no file paths or source URLs: they can contain
        # camera credentials.
        status = self.coordinator.data.status
        return {
            "sleep_state": status.get("sleepState"),
            "item_index": status.get("currentItemIndex"),
            "item_count": status.get("totalItems"),
            "slide_duration": self.coordinator.data.slideshow.get("durationSeconds"),
            "active_playlists": [p["name"] for p in self.coordinator.data.active_playlists],
            "host": self.coordinator.api.host,
        }

    async def _run(self, coro) -> None:
        await coro
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        status = self.coordinator.data.status
        if status.get("isRunning"):
            await self._run(self.coordinator.api.resume())
            return
        # Stopped: restart whatever was selected last.
        selection = await self.coordinator.api.get_playback_selection()
        ids = (selection.get("quickMixState") or {}).get("enabledSavedPlaylistIds")
        if not ids and self.coordinator.data.user_playlists:
            ids = [self.coordinator.data.user_playlists[0]["id"]]
        await self._run(self.coordinator.api.play_playlists(ids or [], "Home Assistant"))

    async def async_media_pause(self) -> None:
        await self._run(self.coordinator.api.pause())

    async def async_media_stop(self) -> None:
        await self._run(self.coordinator.api.stop())

    async def async_media_next_track(self) -> None:
        await self._run(self.coordinator.api.next())

    async def async_media_previous_track(self) -> None:
        await self._run(self.coordinator.api.previous())

    async def async_turn_on(self) -> None:
        await self._run(self.coordinator.api.set_display_power(True))

    async def async_turn_off(self) -> None:
        await self._run(self.coordinator.api.set_display_power(False))

    async def async_set_volume_level(self, volume: float) -> None:
        await self._run(self.coordinator.api.set_volume(round(volume * 100)))

    async def async_mute_volume(self, mute: bool) -> None:
        await self._run(self.coordinator.api.set_mute(mute))

    async def async_set_shuffle(self, shuffle: bool) -> None:
        await self._run(
            self.coordinator.api.update_slideshow_settings(randomizeOrder=shuffle)
        )

    async def async_play_playlists(self, playlists: list[str]) -> None:
        """Mix one or more saved playlists (the frame's "quick mix")."""
        by_name = {p["name"]: p for p in self.coordinator.data.user_playlists}
        unknown = [name for name in playlists if name not in by_name]
        if unknown or not playlists:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_playlist",
                translation_placeholders={
                    "playlists": ", ".join(unknown) or "-",
                    "available": ", ".join(by_name) or "-",
                },
            )
        chosen = [by_name[name] for name in dict.fromkeys(playlists)]
        await self._run(
            self.coordinator.api.play_playlists(
                [p["id"] for p in chosen], " + ".join(p["name"] for p in chosen)
            )
        )

    async def async_select_source(self, source: str) -> None:
        playlist = next(
            p for p in self.coordinator.data.user_playlists if p["name"] == source
        )
        await self._run(
            self.coordinator.api.play_playlists([playlist["id"]], playlist["name"])
        )
