"""The Dynaframe integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigEntry,
)
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, discovery_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import DynaframeApi
from .const import CARD_URL, CONF_AUTO_ADD, DOMAIN, STORE_CARD_URL
from .coordinator import DynaframeCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type DynaframeConfigEntry = ConfigEntry[DynaframeCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard cards and load them on every frontend."""
    frontend = Path(__file__).parent / "frontend"
    cards = {
        CARD_URL: frontend / "dynaframe-card.js",
        STORE_CARD_URL: frontend / "dynaframe-store-card.js",
    }
    await hass.http.async_register_static_paths(
        [StaticPathConfig(url, str(path), cache_headers=False) for url, path in cards.items()]
    )
    for url, path in cards.items():
        # Cache-bust with the file's mtime so browsers pick up every card change.
        stamp = int((await hass.async_add_executor_job(path.stat)).st_mtime)
        add_extra_js_url(hass, f"{url}?v={stamp}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DynaframeConfigEntry) -> bool:
    """Set up a Dynaframe from a config entry."""
    api = DynaframeApi(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = DynaframeCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    offered: set[str] = set()

    @callback
    def _discover_peers() -> None:
        """Frames know each other; offer every frame this one has seen."""
        for peer in coordinator.data.peers:
            ip = peer.get("ipAddress")
            if not peer.get("isOnline") or not ip or ip in offered:
                continue
            offered.add(ip)
            discovery_flow.async_create_flow(
                hass,
                DOMAIN,
                context={"source": SOURCE_INTEGRATION_DISCOVERY},
                data={
                    CONF_HOST: ip,
                    "frame_id": peer.get("frameId"),
                    "name": peer.get("frameName"),
                },
            )

    _discover_peers()
    entry.async_on_unload(coordinator.async_add_listener(_discover_peers))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DynaframeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: DynaframeConfigEntry) -> None:
    """With auto-add on, a deleted frame would come straight back; ignore it instead."""
    if entry.source == SOURCE_IGNORE or not entry.unique_id:
        return
    if not any(
        other.options.get(CONF_AUTO_ADD)
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry.entry_id and other.source != SOURCE_IGNORE
    ):
        return
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IGNORE},
        data={"unique_id": entry.unique_id, "title": entry.title},
    )
