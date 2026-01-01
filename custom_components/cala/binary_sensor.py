"""Binary sensor platform for Cala integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CalaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="status",
        name="Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="safetyLockout",
        name="Safety Lockout",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="compRunning",
        name="Compressor Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fanPwr",
        name="Fan Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cala binary sensor entities."""
    coordinator: CalaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    if coordinator.data:
        for heater_id, heater_data in coordinator.data.items():
            for description in BINARY_SENSOR_DESCRIPTIONS:
                entities.append(
                    CalaBinarySensor(coordinator, heater_id, heater_data, description)
                )
    
    async_add_entities(entities)


class CalaBinarySensor(CoordinatorEntity[CalaDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a Cala binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CalaDataUpdateCoordinator,
        heater_id: str,
        heater_data: dict[str, Any],
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor entity."""
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
        if self.coordinator.data:
            return self.coordinator.data.get(self._heater_id, {})
        return {}

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value = self._heater_data.get(self.entity_description.key)
        if value is None:
            return None
        # Handle status field which is a string like "CONNECTED"
        if self.entity_description.key == "status":
            return value == "CONNECTED"
        return bool(value)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._heater_id in self.coordinator.data
        )
