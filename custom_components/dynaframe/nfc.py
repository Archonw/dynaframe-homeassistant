"""Pass tags scanned on a frame's NFC reader on to Home Assistant's tags."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.tag import async_scan_tag
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval

from .api import DynaframeError
from .const import DOMAIN, NFC_SCAN_INTERVAL
from .coordinator import DynaframeCoordinator

_LOGGER = logging.getLogger(__name__)


class NfcScanWatcher:
    """Polls the frame's last NFC scan, but only while it has a reader.

    DynaFrame offers scan events only via MQTT; the Engine does remember the
    last scan (tag and time), so a new time means a new scan. Each one becomes
    a regular Home Assistant tag scan ("Tag scanned" trigger, Settings → Tags).
    """

    def __init__(self, hass: HomeAssistant, coordinator: DynaframeCoordinator) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._unsub_timer: CALLBACK_TYPE | None = None
        self._last: tuple[str, str] | None = None
        self._primed = False
        self._busy = False

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Follow the coordinator; returns the function that stops watching."""
        unsub_listener = self._coordinator.async_add_listener(self._async_update_timer)
        self._async_update_timer()

        @callback
        def _stop() -> None:
            unsub_listener()
            self._async_stop_timer()

        return _stop

    @callback
    def _async_update_timer(self) -> None:
        has_reader = bool(self._coordinator.data and self._coordinator.data.nfc_readers)
        if has_reader and self._unsub_timer is None:
            _LOGGER.debug("%s has an NFC reader, watching for scans", self._coordinator.name)
            self._unsub_timer = async_track_time_interval(
                self._hass, self._async_poll, NFC_SCAN_INTERVAL, cancel_on_shutdown=True
            )
        elif not has_reader:
            self._async_stop_timer()

    @callback
    def _async_stop_timer(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None
        # Whatever the frame remembers by the next start is old news.
        self._primed = False

    async def _async_poll(self, _now: datetime) -> None:
        if self._busy or not self._coordinator.last_update_success:
            return
        self._busy = True
        try:
            scan = await self._coordinator.api.get_recent_nfc_scan()
        except DynaframeError as err:
            _LOGGER.debug("%s: NFC scan not read: %s", self._coordinator.name, err)
            return
        finally:
            self._busy = False
        current = (scan["tagId"], str(scan.get("scannedAt"))) if scan else None
        if not self._primed:
            # A scan from before Home Assistant (re)started is not passed on.
            self._last, self._primed = current, True
            return
        if current is None or current == self._last:
            return
        self._last = current
        await async_scan_tag(self._hass, current[0], self._device_id())

    def _device_id(self) -> str | None:
        device = dr.async_get(self._hass).async_get_device(
            identifiers={(DOMAIN, self._coordinator.config_entry.unique_id)}
        )
        return device.id if device else None
