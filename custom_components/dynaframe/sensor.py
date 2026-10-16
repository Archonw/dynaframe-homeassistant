"""Sensors for Dynaframe."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DynaframeConfigEntry
from .coordinator import DynaframeData
from .entity import DynaframeEntity


@dataclass(frozen=True, kw_only=True)
class DynaframeSensorDescription(SensorEntityDescription):
    value_fn: Callable[[DynaframeData], Any]
    attrs_fn: Callable[[DynaframeData], dict[str, Any]] | None = None


# Metadata of the current item that is safe to show. File paths and source
# URLs are left out on purpose: stream URLs can contain camera credentials.
METADATA_FIELDS = {
    "fileName": "file_name",
    "title": "title",
    "author": "author",
    "subject": "subject",
    "description": "description",
    "keywords": "keywords",
    "tags": "tags",
    "dateTaken": "date_taken",
    "make": "camera_make",
    "model": "camera_model",
    "width": "width",
    "height": "height",
    "copyright": "copyright",
    "mediaType": "media_type",
    "source": "source",
}


def _item_metadata(data: DynaframeData) -> dict[str, Any]:
    item = data.status.get("currentItem") or {}
    return {attr: item[key] for key, attr in METADATA_FIELDS.items() if item.get(key) not in (None, "")}


def _disk(data: DynaframeData, media: bool) -> dict[str, Any] | None:
    disks = data.disks
    if media:
        return next((d for d in disks if "Pictures" in d.get("drive", "")), None) or next(
            (d for d in disks if d.get("drive") == "/"), None
        )
    return next((d for d in disks if d.get("drive") == "/"), None)


def _disk_used(data: DynaframeData, media: bool) -> float | None:
    disk = _disk(data, media)
    # The frame calls this field "freePercent" but it is the used share.
    try:
        return float(disk["freePercent"]) if disk else None
    except (KeyError, TypeError, ValueError):
        return None


def _disk_attrs(data: DynaframeData, media: bool) -> dict[str, Any]:
    disk = _disk(data, media) or {}
    return {
        "drive": disk.get("drive"),
        "total": disk.get("totalSize"),
        "used": disk.get("used"),
        "available": disk.get("available"),
    }


def _sync_attrs(data: DynaframeData) -> dict[str, Any]:
    sync = data.sync
    names = {f.get("frameId"): f.get("frameName") for f in data.peers}
    return {
        "leader": sync.get("leaderName"),
        "synced_frames": [names.get(i, i) for i in sync.get("syncedFrameIds") or []],
        "known_frames": [f.get("frameName") for f in data.peers if not f.get("frameId") == sync.get("frameId")],
    }


SENSORS = (
    DynaframeSensorDescription(
        key="current_item",
        translation_key="current_item",
        value_fn=lambda d: (d.status.get("currentItem") or {}).get("title")
        or (d.status.get("currentItem") or {}).get("fileName"),
        attrs_fn=_item_metadata,
    ),
    DynaframeSensorDescription(
        key="sync_role",
        translation_key="sync_role",
        device_class=SensorDeviceClass.ENUM,
        options=["independent", "leader", "follower"],
        value_fn=lambda d: d.sync.get("syncRole"),
        attrs_fn=_sync_attrs,
    ),
    DynaframeSensorDescription(
        key="memory_used",
        translation_key="memory_used",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d: d.memory.get("percentUsed"),
        attrs_fn=lambda d: {
            "total": d.memory.get("totalFormatted"),
            "available": d.memory.get("availableFormatted"),
        },
    ),
    DynaframeSensorDescription(
        key="media_storage_used",
        translation_key="media_storage_used",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _disk_used(d, media=True),
        attrs_fn=lambda d: _disk_attrs(d, media=True),
    ),
    DynaframeSensorDescription(
        key="system_storage_used",
        translation_key="system_storage_used",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _disk_used(d, media=False),
        attrs_fn=lambda d: _disk_attrs(d, media=False),
    ),
    DynaframeSensorDescription(
        key="sleep_state",
        translation_key="sleep_state",
        value_fn=lambda d: d.status.get("sleepState"),
    ),
    DynaframeSensorDescription(
        key="version",
        translation_key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.update.get("installedVersion"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynaframeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        DynaframeSensor(entry.runtime_data, description) for description in SENSORS
    )


class DynaframeSensor(DynaframeEntity, SensorEntity):
    entity_description: DynaframeSensorDescription

    def __init__(self, coordinator, description: DynaframeSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
