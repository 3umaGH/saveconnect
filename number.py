"""Number platform for the SaveConnect integration.

Covers the temperature setpoint plus the timed "boost" mode registers
(Crowded / Refresh / Fireplace). Units are confirmed against the
systemair_modbus integration's SaveModel.REGISTERS, which targets the same
VSR300 register map over native Modbus: Refresh and Fireplace are minutes,
but Crowded is HOURS. Away and Holiday boost registers are intentionally not
exposed yet (hours / days respectively) since we have no confirmed working
example to validate against.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOST,
    DOMAIN,
    KEY_BOOST_CROWDED,
    KEY_BOOST_FIREPLACE,
    KEY_BOOST_REFRESH,
    KEY_TEMPERATURE_SETPOINT,
    KEY_UNKNOWN_16100,
    MODE_WRITE_BUNDLE_KEYS,
)
from .coordinator import SaveConnectCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SaveConnectNumberDescription(NumberEntityDescription):
    """Describes a SaveConnect number entity backed by a register."""

    register_key: str = ""
    divide_by: int = 1
    bundle_write: bool = False


DESCRIPTIONS: tuple[SaveConnectNumberDescription, ...] = (
    SaveConnectNumberDescription(
        key="temperature_setpoint",
        register_key=KEY_TEMPERATURE_SETPOINT,
        divide_by=10,
        bundle_write=True,
        name="Temperature Setpoint",
        native_min_value=12,
        native_max_value=30,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        icon="mdi:thermostat",
    ),
    SaveConnectNumberDescription(
        key="crowded_boost_hours",
        register_key=KEY_BOOST_CROWDED,
        divide_by=1,
        bundle_write=False,
        name="Crowded Boost",
        native_min_value=0,
        native_max_value=72,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        icon="mdi:account-group",
    ),
    SaveConnectNumberDescription(
        key="refresh_boost_minutes",
        register_key=KEY_BOOST_REFRESH,
        divide_by=1,
        bundle_write=False,
        name="Refresh Boost",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        icon="mdi:autorenew",
    ),
    SaveConnectNumberDescription(
        key="fireplace_boost_minutes",
        register_key=KEY_BOOST_FIREPLACE,
        divide_by=1,
        bundle_write=False,
        name="Fireplace Boost",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.BOX,
        icon="mdi:fireplace",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SaveConnect number entities from a config entry."""
    coordinator: SaveConnectCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SaveConnectNumber(coordinator, entry, description) for description in DESCRIPTIONS
    )


class SaveConnectNumber(CoordinatorEntity[SaveConnectCoordinator], NumberEntity):
    """A single writable SaveConnect register exposed as a number entity."""

    entity_description: SaveConnectNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SaveConnectCoordinator,
        entry: ConfigEntry,
        description: SaveConnectNumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SaveConnect",
            manufacturer="Systemair",
            model="SAVE VSR300",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.data.get(self.entity_description.register_key)
        if raw is None:
            return None
        return raw / self.entity_description.divide_by

    async def async_set_native_value(self, value: float) -> None:
        raw_value = round(value * self.entity_description.divide_by)

        if self.entity_description.bundle_write:
            # Mirror the SaveConnect web UI's captured mwrite traffic: it
            # always re-submits the whole mode-change field bundle together,
            # with 16100 always sent as literal 0.
            payload = {
                key: self.coordinator.data.get(key, 0) for key in MODE_WRITE_BUNDLE_KEYS
            }
            payload[KEY_UNKNOWN_16100] = 0
            payload[self.entity_description.register_key] = raw_value
        else:
            payload = {self.entity_description.register_key: raw_value}

        _LOGGER.debug(
            "Writing SaveConnect register %s = %s (%s)",
            self.entity_description.register_key,
            raw_value,
            payload,
        )
        await self.coordinator.async_write_registers(payload)
