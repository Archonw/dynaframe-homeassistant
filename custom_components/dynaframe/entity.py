"""Base entity for Dynaframe."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import pretty_name
from .const import DOMAIN
from .coordinator import DynaframeCoordinator


class DynaframeEntity(CoordinatorEntity[DynaframeCoordinator]):
    """Common device info and unique ids."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DynaframeCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=pretty_name(entry.data.get(CONF_NAME, entry.title)),
            manufacturer="Dynaframe",
            model="Dynaframe",
            sw_version=coordinator.data.update.get("installedVersion"),
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )
