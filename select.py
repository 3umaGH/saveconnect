"""Select platform for the SaveConnect integration (user mode)."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOST,
    DOMAIN,
    KEY_UNKNOWN_16100,
    KEY_USER_MODE_ACTIVE,
    KEY_USER_MODE_REQUEST,
    MODE_WRITE_BUNDLE_KEYS,
    REQUEST_USER_MODES,
    STATUS_USER_MODES,
)
from .coordinator import SaveConnectCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SaveConnect user mode select entity."""
    coordinator: SaveConnectCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SaveConnectUserModeSelect(coordinator, entry)])


class SaveConnectUserModeSelect(CoordinatorEntity[SaveConnectCoordinator], SelectEntity):
    """User mode select entity (Auto/Manual/Crowded/Refresh/Fireplace/Away/Holiday)."""

    _attr_has_entity_name = True
    _attr_name = "User Mode"
    _attr_options = list(REQUEST_USER_MODES.keys())
    _attr_icon = "mdi:fan-auto"

    def __init__(self, coordinator: SaveConnectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_user_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SaveConnect",
            manufacturer="Systemair",
            model="SAVE VSR300",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def current_option(self) -> str | None:
        # Register 1160 (status) is 0-indexed - a different enum than the
        # 1-indexed 1161 (request) register used to change it.
        raw = self.coordinator.data.get(KEY_USER_MODE_ACTIVE)
        if raw is None:
            return None
        return STATUS_USER_MODES.get(raw)

    async def async_select_option(self, option: str) -> None:
        mode_value = REQUEST_USER_MODES[option]
        # Mirror the SaveConnect web UI's captured mwrite traffic: it always
        # re-submits the whole mode-change field bundle, not just the one
        # field the user touched, with 16100 always sent as literal 0.
        payload = {
            key: self.coordinator.data.get(key, 0) for key in MODE_WRITE_BUNDLE_KEYS
        }
        payload[KEY_USER_MODE_REQUEST] = mode_value
        payload[KEY_UNKNOWN_16100] = 0
        _LOGGER.debug("Setting SaveConnect user mode to %s (%s)", option, payload)
        await self.coordinator.async_write_registers(payload)
