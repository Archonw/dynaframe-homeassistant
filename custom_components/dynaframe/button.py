"""Maintenance buttons for Dynaframe."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
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
    async_add_entities([RebootButton(entry.runtime_data)])


class RebootButton(DynaframeEntity, ButtonEntity):
    """Reboots the whole device (the web UI offers no app-only restart)."""

    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "reboot")

    async def async_press(self) -> None:
        await self.coordinator.api.reboot()
