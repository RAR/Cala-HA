"""Number platform for Cala integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import CalaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="boost_duration",
        name="Boost Duration",
        icon="mdi:timer",
        native_min_value=1,
        native_max_value=24,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="vacation_duration",
        name="Vacation Duration",
        icon="mdi:calendar-clock",
        native_min_value=1,
        native_max_value=90,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cala number entities."""
    coordinator: CalaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    if coordinator.data:
        for heater_id, heater_data in coordinator.data.items():
            for description in NUMBER_DESCRIPTIONS:
                entities.append(
                    CalaDurationNumber(coordinator, heater_id, heater_data, description)
                )
    
    async_add_entities(entities)


class CalaDurationNumber(CoordinatorEntity[CalaDataUpdateCoordinator], NumberEntity, RestoreEntity):
    """Representation of a Cala duration number."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CalaDataUpdateCoordinator,
        heater_id: str,
        heater_data: dict[str, Any],
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
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
        
        # Set default values
        if description.key == "boost_duration":
            self._attr_native_value = 4.0  # 4 hours default
        elif description.key == "vacation_duration":
            self._attr_native_value = 7.0  # 7 days default

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                self._attr_native_value = float(last_state.state)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
