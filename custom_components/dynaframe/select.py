"""Playlist selection for Dynaframe."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DynaframeConfigEntry
from .const import TRANSITIONS
from .entity import DynaframeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynaframeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            PlaylistSelect(coordinator),
            TransitionSelect(coordinator),
            OverlaySelect(coordinator),
        ]
    )


class PlaylistSelect(DynaframeEntity, SelectEntity):
    _attr_translation_key = "playlist"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "playlist")

    @property
    def options(self) -> list[str]:
        return [p["name"] for p in self.coordinator.data.user_playlists]

    @property
    def current_option(self) -> str | None:
        playlist = self.coordinator.data.current_playlist
        return playlist.get("name") if playlist else None

    async def async_select_option(self, option: str) -> None:
        playlist = next(
            p for p in self.coordinator.data.user_playlists if p["name"] == option
        )
        await self.coordinator.api.play_playlists([playlist["id"]], playlist["name"])
        await self.coordinator.async_request_refresh()


class TransitionSelect(DynaframeEntity, SelectEntity):
    _attr_translation_key = "transition"
    _attr_options = TRANSITIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "transition")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.transition

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_transition(option)
        await self.coordinator.async_request_refresh()


NO_OVERLAY = "—"


class OverlaySelect(DynaframeEntity, SelectEntity):
    """Default overlay; options are labels, mapped back to overlay file names."""

    _attr_translation_key = "default_overlay"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "default_overlay")

    @property
    def _choices(self) -> dict[str, str]:
        choices = {NO_OVERLAY: ""}
        for overlay in self.coordinator.data.overlays:
            file_name = overlay.get("fileName") or overlay.get("name")
            label = overlay.get("name") or file_name
            if "portrait" in file_name:
                label += " (Portrait)"
            elif "landscape" in file_name:
                label += " (Landscape)"
            while label in choices:
                label += " ·"
            choices[label] = file_name
        return choices

    @property
    def options(self) -> list[str]:
        return list(self._choices)

    @property
    def current_option(self) -> str | None:
        current = self.coordinator.data.slideshow.get("defaultOverlay") or ""
        return next((k for k, v in self._choices.items() if v == current), None)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_default_overlay(
            self._choices[option], self.coordinator.data.slideshow
        )
        await self.coordinator.async_request_refresh()
