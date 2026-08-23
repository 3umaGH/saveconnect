"""Config flow for the SaveConnect integration."""

from __future__ import annotations

import json
from urllib.parse import quote
from typing import Any

import async_timeout
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    QUERY_REGISTERS,
)

_QUERY_STRING = quote(json.dumps(QUERY_REGISTERS, separators=(",", ":")), safe="{}:,")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5)
        ),
    }
)


async def _validate_host(hass: HomeAssistant, host: str) -> None:
    """Raise CannotConnect if the device cannot be reached."""
    session = async_get_clientsession(hass)
    url = f"http://{host}/mread?{_QUERY_STRING}"
    async with async_timeout.timeout(10):
        response = await session.get(url)
        response.raise_for_status()
        await response.json(content_type=None)


class SaveConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SaveConnect."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            try:
                await _validate_host(self.hass, user_input[CONF_HOST])
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SaveConnectOptionsFlow:
        return SaveConnectOptionsFlow(config_entry)


class SaveConnectOptionsFlow(config_entries.OptionsFlow):
    """Handle options for SaveConnect (scan interval)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=5)
                    )
                }
            ),
        )
