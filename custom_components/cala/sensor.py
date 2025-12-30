"""Sensor platform for Cala integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CalaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="topTankRawTemp",
        name="Top Tank Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="outletTemp",
        name="Outlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inletTemp",
        name="Inlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ambientTemp",
        name="Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="averageTankTempHigh24",
        name="Average Tank Temperature (24h)",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="gallonsUsedSum",
        name="Total Water Used",
        native_unit_of_measurement=UnitOfVolume.GALLONS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="litersUsedSinceLastBoot",
        name="Water Used Since Boot",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="flowRate",
        name="Water Flow Rate",
        native_unit_of_measurement=UnitOfVolumeFlowRate.GALLONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-pump",
    ),
    SensorEntityDescription(
        key="highEnergyUsage24",
        name="Energy Usage (24h)",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="suctionPressure",
        name="Suction Pressure",
        native_unit_of_measurement="psi",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="deliveryPressure",
        name="Delivery Pressure",
        native_unit_of_measurement="psi",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="compSpeed",
        name="Compressor Speed",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    SensorEntityDescription(
        key="fanPwm",
        name="Fan Speed",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    SensorEntityDescription(
        key="userDesiredTemp",
        name="Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="userMaxTemp",
        name="Maximum Temperature Setting",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cala sensor entities."""
    coordinator: CalaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    for heater_id, heater_data in coordinator.data.items():
        for description in SENSOR_DESCRIPTIONS:
            # Only add sensor if the heater has this data
            if description.key in heater_data:
                entities.append(
                    CalaSensor(coordinator, heater_id, heater_data, description)
                )
    
    async_add_entities(entities)


class CalaSensor(CoordinatorEntity[CalaDataUpdateCoordinator], SensorEntity):
    """Representation of a Cala sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CalaDataUpdateCoordinator,
        heater_id: str,
        heater_data: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._heater_id = heater_id
        self.entity_description = description
        self._attr_unique_id = f"cala_{heater_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, heater_id)},
            "name": heater_data.get("name", "Cala Water Heater"),
            "manufacturer": "Cala Systems",
            "model": heater_data.get("model", "Heat Pump Water Heater"),
            "sw_version": heater_data.get("firmware_version"),
        }

    @property
    def _heater_data(self) -> dict[str, Any]:
        """Get current heater data from coordinator."""
        return self.coordinator.data.get(self._heater_id, {})

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self._heater_data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._heater_id in self.coordinator.data
        )
