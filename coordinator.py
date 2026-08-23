"""Data update coordinator for SaveConnect."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from urllib.parse import quote

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, QUERY_REGISTERS

_LOGGER = logging.getLogger(__name__)

_QUERY_STRING = quote(json.dumps(QUERY_REGISTERS, separators=(",", ":")), safe="{}:,")


class SaveConnectCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Poll the SaveConnect device and hand out the parsed register values."""

    def __init__(self, hass: HomeAssistant, host: str, scan_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._host = host
        self._url = f"http://{host}/mread?{_QUERY_STRING}"

    async def _async_update_data(self) -> dict[str, int]:
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.get(self._url)
                response.raise_for_status()
                return await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001 - surface any failure as UpdateFailed
            raise UpdateFailed(f"Error communicating with SaveConnect device: {err}") from err

    async def async_write_registers(self, values: dict[str, int]) -> None:
        """Write one or more registers, then refresh cached state.

        `values` keys must be strings matching the device's register IDs.
        """
        query_string = quote(json.dumps(values, separators=(",", ":")), safe="{}:,")
        url = f"http://{self._host}/mwrite?{query_string}"
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await session.get(url)
                response.raise_for_status()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error writing to SaveConnect device: {err}") from err

        # Reflect the change immediately instead of waiting for the next poll.
        if self.data is not None:
            self.async_set_updated_data({**self.data, **values})
        await self.async_request_refresh()
