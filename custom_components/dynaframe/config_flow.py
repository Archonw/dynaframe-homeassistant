"""Config flow for Dynaframe: manual, zeroconf, DHCP and peer discovery."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components import network
from homeassistant.config_entries import (
    SOURCE_IGNORE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import DynaframeApi, DynaframeError
from .const import CONF_AUTO_ADD, DOMAIN

_LOGGER = logging.getLogger(__name__)

MANUAL = "manual"
SCAN_TIMEOUT = aiohttp.ClientTimeout(total=2)
SCAN_PARALLEL = 64


def pretty_name(name: str) -> str:
    """dynaframe-fenster -> Dynaframe Fenster."""
    return " ".join(part.capitalize() for part in name.replace("_", "-").split("-"))


class DynaframeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynaframe."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return DynaframeOptionsFlow()

    def _auto_add_enabled(self) -> bool:
        """Auto-add is a household-wide choice; any frame having it counts."""
        return any(
            entry.options.get(CONF_AUTO_ADD)
            for entry in self._async_current_entries(include_ignore=False)
        )

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None
        self._found: dict[str, str] = {}

    async def _async_scan(self) -> dict[str, str]:
        """Probe every address of the local IPv4 networks; return {ip: name}."""
        hosts: set[str] = set()
        for adapter in await network.async_get_adapters(self.hass):
            if not adapter["enabled"]:
                continue
            for addr in adapter["ipv4"]:
                net = ipaddress.ip_network(
                    f"{addr['address']}/{max(addr['network_prefix'], 24)}", strict=False
                )
                if net.is_loopback or not net.is_private:
                    continue
                hosts.update(str(ip) for ip in net.hosts())
        session = async_get_clientsession(self.hass)
        semaphore = asyncio.Semaphore(SCAN_PARALLEL)
        found: dict[str, str] = {}

        async def probe(ip: str) -> None:
            async with semaphore:
                try:
                    async with session.get(
                        f"http://{ip}/Sync/GetSyncStatus", timeout=SCAN_TIMEOUT
                    ) as resp:
                        if resp.status != 200:
                            return
                        info = await resp.json(content_type=None)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    return
            if isinstance(info, dict) and info.get("frameId"):
                found[ip] = info.get("frameName") or ip

        await asyncio.gather(*(probe(ip) for ip in hosts))
        _LOGGER.debug("Network scan found %s", found)
        return found

    async def _async_probe(self, host: str) -> tuple[str, str]:
        """Return (frame_id, frame_name) or raise DynaframeError."""
        api = DynaframeApi(async_get_clientsession(self.hass), host)
        info = await api.get_sync_status()
        if not info.get("frameId"):
            raise DynaframeError("not a Dynaframe")
        return info["frameId"], info.get("frameName") or host

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Scan the network and offer every frame that is not set up yet."""
        configured = {
            entry.data.get(CONF_HOST) for entry in self._async_current_entries()
        }
        self._found = {
            ip: name
            for ip, name in (await self._async_scan()).items()
            if ip not in configured
        }
        if not self._found:
            return await self.async_step_manual()
        return await self.async_step_pick()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input[CONF_HOST] == MANUAL:
                return await self.async_step_manual()
            try:
                return await self._async_create_from_host(user_input[CONF_HOST])
            except DynaframeError:
                return self.async_abort(reason="cannot_connect")
        options = [
            SelectOptionDict(value=ip, label=f"{pretty_name(name)} ({ip})")
            for ip, name in sorted(self._found.items())
        ]
        options.append(SelectOptionDict(value=MANUAL, label="Manuell eingeben / Enter manually"))
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): SelectSelector(
                        SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                return await self._async_create_from_host(user_input[CONF_HOST].strip())
            except DynaframeError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def _async_create_from_host(self, host: str) -> ConfigFlowResult:
        frame_id, name = await self._async_probe(host)
        # A pending discovery of the same frame must not block manual setup.
        await self.async_set_unique_id(frame_id, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(
            title=pretty_name(name), data={CONF_HOST: host, CONF_NAME: name}
        )

    async def _async_handle_discovery(self, host: str) -> ConfigFlowResult:
        _LOGGER.debug("Discovered possible Dynaframe at %s via %s", host, self.source)
        self._async_abort_entries_match({CONF_HOST: host})
        try:
            frame_id, name = await self._async_probe(host)
        except DynaframeError:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(frame_id)
        # A known frame with a new IP address is updated silently.
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._host, self._name = host, name
        if self._auto_add_enabled():
            _LOGGER.info("Adding discovered Dynaframe %s (%s) automatically", name, host)
            return self.async_create_entry(
                title=pretty_name(name),
                data={CONF_HOST: host, CONF_NAME: name},
                options={CONF_AUTO_ADD: True},
            )
        self.context["title_placeholders"] = {"name": pretty_name(name)}
        return await self.async_step_discovery_confirm()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        if discovery_info.ip_address.version != 4:
            return self.async_abort(reason="not_ipv4")
        return await self._async_handle_discovery(discovery_info.host)

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        return await self._async_handle_discovery(discovery_info.ip)

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        if frame_id := discovery_info.get("frame_id"):
            await self.async_set_unique_id(frame_id)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: discovery_info[CONF_HOST]}
            )
        return await self._async_handle_discovery(discovery_info[CONF_HOST])

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._host and self._name
        if user_input is not None:
            return self.async_create_entry(
                title=pretty_name(self._name),
                data={CONF_HOST: self._host, CONF_NAME: self._name},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": pretty_name(self._name),
                "host": self._host,
            },
        )


class DynaframeOptionsFlow(OptionsFlow):
    """Options shared by all frames."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Keep the setting identical on every frame.
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    entry.entry_id != self.config_entry.entry_id
                    and entry.source != SOURCE_IGNORE
                ):
                    self.hass.config_entries.async_update_entry(
                        entry, options={**entry.options, **user_input}
                    )
            return self.async_create_entry(
                data={**self.config_entry.options, **user_input}
            )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTO_ADD,
                        default=self.config_entry.options.get(CONF_AUTO_ADD, False),
                    ): bool
                }
            ),
        )
