"""Switches for Dynaframe."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DynaframeConfigEntry
from .entity import DynaframeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynaframeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DisplaySwitch(coordinator),
            ShuffleSwitch(coordinator),
            VideoAudioSwitch(coordinator),
            MuteSwitch(coordinator),
            OverlaysSwitch(coordinator),
        ]
    )


class DisplaySwitch(DynaframeEntity, SwitchEntity):
    _attr_translation_key = "display"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "display")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.display_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_display_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_display_power(False)
        await self.coordinator.async_request_refresh()


class MuteSwitch(DynaframeEntity, SwitchEntity):
    _attr_translation_key = "mute"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mute")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.volume.get("muted")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_mute(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_mute(False)
        await self.coordinator.async_request_refresh()


class OverlaysSwitch(DynaframeEntity, SwitchEntity):
    _attr_translation_key = "overlays"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "overlays")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.slideshow.get("overlaysEnabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_overlays_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_overlays_enabled(False)
        await self.coordinator.async_request_refresh()


class _SlideshowSettingSwitch(DynaframeEntity, SwitchEntity):
    _setting: str

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, self._attr_translation_key)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.slideshow.get(self._setting)

    async def _set(self, value: bool) -> None:
        await self.coordinator.api.update_slideshow_settings(**{self._setting: value})
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class ShuffleSwitch(_SlideshowSettingSwitch):
    _attr_translation_key = "shuffle"
    _setting = "randomizeOrder"


class VideoAudioSwitch(_SlideshowSettingSwitch):
    _attr_translation_key = "video_audio"
    _setting = "playVideoAudio"
