"""Button platform for Cala integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, sanitize_entity_id
from .coordinator import CalaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="boost_mode",
        name="Boost Mode",
        icon="mdi:rocket-launch",
    ),
    ButtonEntityDescription(
        key="cancel_boost",
        name="Cancel Boost",
        icon="mdi:cancel",
    ),
    ButtonEntityDescription(
        key="vacation_mode",
        name="Vacation Mode",
        icon="mdi:airplane",
    ),
    ButtonEntityDescription(
        key="cancel_vacation",
        name="Cancel Vacation",
        icon="mdi:cancel",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cala button entities."""
    coordinator: CalaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    if coordinator.data:
        for heater_id, heater_data in coordinator.data.items():
            for description in BUTTON_DESCRIPTIONS:
                entities.append(
                    CalaModeButton(coordinator, heater_id, heater_data, description)
                )
    
    async_add_entities(entities)


class CalaModeButton(CoordinatorEntity[CalaDataUpdateCoordinator], ButtonEntity):
    """Representation of a Cala mode button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CalaDataUpdateCoordinator,
        heater_id: str,
        heater_data: dict[str, Any],
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._heater_id = heater_id
        self.entity_description = description
        self._attr_unique_id = f"cala_{sanitize_entity_id(heater_id)}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, heater_id)},
            "name": heater_data.get("name", "Cala Water Heater"),
            "manufacturer": "Cala Systems",
            "model": heater_data.get("model", "Heat Pump Water Heater"),
            "sw_version": heater_data.get("firmware_version"),
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        key = self.entity_description.key
        
        if key == "boost_mode":
            # Get boost duration from number entity
            number_entity_id = f"number.{self._attr_device_info['name'].lower().replace(' ', '_')}_boost_duration"
            duration_hours = self.hass.states.get(number_entity_id)
            hours = int(duration_hours.state) if duration_hours else 4  # Default 4 hours
            await self.coordinator.async_set_operation_mode(self._heater_id, "boost", hours)
        elif key == "cancel_boost":
            await self.coordinator.async_cancel_boost(self._heater_id)
        elif key == "vacation_mode":
            # Get vacation duration from number entity
            number_entity_id = f"number.{self._attr_device_info['name'].lower().replace(' ', '_')}_vacation_duration"
            duration_days = self.hass.states.get(number_entity_id)
            days = int(duration_days.state) if duration_days else 7  # Default 7 days
            await self.coordinator.async_set_operation_mode(self._heater_id, "vacation", days)
        elif key == "cancel_vacation":
            await self.coordinator.async_cancel_vacation(self._heater_id)
        
        await self.coordinator.async_request_refresh()
