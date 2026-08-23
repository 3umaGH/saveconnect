"""Sensor platform for the SaveConnect integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOST,
    DOMAIN,
    KEY_EAT,
    KEY_EXTRACT_FAN_RPM,
    KEY_FILTER_TIME_REMAINING_HIGH,
    KEY_FILTER_TIME_REMAINING_LOW,
    KEY_HUMIDITY,
    KEY_OAT,
    KEY_OHT,
    KEY_SAT,
    KEY_SUPPLY_FAN_RPM,
)
from .coordinator import SaveConnectCoordinator


@dataclass(frozen=True, kw_only=True)
class SaveConnectSensorDescription(SensorEntityDescription):
    """Describes a SaveConnect sensor backed by a single register."""

    register_key: str = ""
    divide_by: int = 1


SENSOR_DESCRIPTIONS: tuple[SaveConnectSensorDescription, ...] = (
    SaveConnectSensorDescription(
        key="outdoor_air_temperature",
        register_key=KEY_OAT,
        divide_by=10,
        name="Outdoor Air Temperature sensor (OAT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SaveConnectSensorDescription(
        key="supply_air_temperature",
        register_key=KEY_SAT,
        divide_by=10,
        name="Supply Air Temperature sensor (SAT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SaveConnectSensorDescription(
        key="overheat_temperature_sensor",
        register_key=KEY_OHT,
        divide_by=10,
        name="Overheat Temperature Sensor (OHT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SaveConnectSensorDescription(
        key="extract_air_temperature",
        register_key=KEY_EAT,
        divide_by=10,
        name="Inbuilt Extract Air Temperature sensor",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SaveConnectSensorDescription(
        key="humidity",
        register_key=KEY_HUMIDITY,
        divide_by=1,
        name="Inbuilt RH",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SaveConnectSensorDescription(
        key="supply_air_fan_level",
        register_key=KEY_SUPPLY_FAN_RPM,
        divide_by=1,
        name="Supply air fan level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        icon="mdi:fan",
    ),
    SaveConnectSensorDescription(
        key="extract_air_fan_level",
        register_key=KEY_EXTRACT_FAN_RPM,
        divide_by=1,
        name="Extract air fan level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        icon="mdi:fan",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SaveConnect sensors from a config entry."""
    coordinator: SaveConnectCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        SaveConnectSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(SaveConnectFilterReplacementSensor(coordinator, entry))
    async_add_entities(entities)


class SaveConnectSensor(CoordinatorEntity[SaveConnectCoordinator], SensorEntity):
    """Representation of a single SaveConnect register as a sensor."""

    entity_description: SaveConnectSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SaveConnectCoordinator,
        entry: ConfigEntry,
        description: SaveConnectSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SaveConnect",
            manufacturer="Systemair",
            model="SAVE",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self) -> float | int | None:
        raw = self.coordinator.data.get(self.entity_description.register_key)
        if raw is None:
            return None
        if self.entity_description.divide_by == 1:
            return raw
        return raw / self.entity_description.divide_by


class SaveConnectFilterReplacementSensor(
    CoordinatorEntity[SaveConnectCoordinator], SensorEntity
):
    """Estimated filter replacement due date.

    Registers 7004 (low word) and 7005 (high word) together hold the
    remaining time in seconds as a 32-bit value. Exposed as a timestamp
    (now + remaining seconds) rather than a raw duration, since a timestamp
    stays accurate in the UI between polls without extra ageing logic.
    """

    _attr_has_entity_name = True
    _attr_name = "Filter Replacement Due"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator: SaveConnectCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_filter_replacement_due"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SaveConnect",
            manufacturer="Systemair",
            model="SAVE",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def native_value(self):
        low = self.coordinator.data.get(KEY_FILTER_TIME_REMAINING_LOW)
        high = self.coordinator.data.get(KEY_FILTER_TIME_REMAINING_HIGH)
        if low is None or high is None:
            return None
        remaining_seconds = low + (high << 16)
        return dt_util.utcnow() + timedelta(seconds=remaining_seconds)
