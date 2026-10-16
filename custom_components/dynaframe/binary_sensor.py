"""Binary sensors for Dynaframe."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DynaframeConfigEntry
from .entity import DynaframeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynaframeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([UpdateAvailableSensor(entry.runtime_data)])


class UpdateAvailableSensor(DynaframeEntity, BinarySensorEntity):
    _attr_translation_key = "update_available"
    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "update_available")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.update.get("updateAvailable")

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        update = self.coordinator.data.update
        return {
            "available_version": update.get("availableVersion"),
            "channel": update.get("channel"),
        }
