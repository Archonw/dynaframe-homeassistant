"""Slide duration, transition duration and volume for Dynaframe."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTime
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
            SlideDurationNumber(coordinator),
            VolumeNumber(coordinator),
            TransitionDurationNumber(coordinator),
        ]
    )


class SlideDurationNumber(DynaframeEntity, NumberEntity):
    _attr_translation_key = "slide_duration"
    _attr_native_min_value = 3
    _attr_native_max_value = 3600
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "slide_duration")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.slideshow.get("durationSeconds")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.update_slideshow_settings(durationSeconds=int(value))
        await self.coordinator.async_request_refresh()


class VolumeNumber(DynaframeEntity, NumberEntity):
    """Volume as its own entity: unlike the media player, it stays visible
    while the display is off."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "volume")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.volume.get("value")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.set_volume(int(value))
        await self.coordinator.async_request_refresh()


class TransitionDurationNumber(DynaframeEntity, NumberEntity):
    """Duration of the current transition effect; stored per effect on the frame."""

    _attr_translation_key = "transition_duration"
    _attr_native_min_value = 0.1
    _attr_native_max_value = 30
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "transition_duration")

    @property
    def available(self) -> bool:
        # "none" swaps images directly and has no duration.
        return super().available and self.coordinator.data.transition_duration is not None

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.transition_duration

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data
        await self.coordinator.api.set_transition_settings(
            data.transition, {**data.transition_settings, "duration": round(value, 2)}
        )
        await self.coordinator.async_request_refresh()
