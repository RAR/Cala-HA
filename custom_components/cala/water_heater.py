"""Water heater platform for Cala integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
    OPERATION_MODE_BOOST,
    OPERATION_MODE_ECO,
    OPERATION_MODE_STANDARD,
    OPERATION_MODE_VACATION,
)
from .coordinator import CalaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

OPERATION_LIST = [
    OPERATION_MODE_STANDARD,
    OPERATION_MODE_ECO,
    OPERATION_MODE_BOOST,
    OPERATION_MODE_VACATION,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cala water heater entities."""
    coordinator: CalaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = []
    for heater_id, heater_data in coordinator.data.items():
        entities.append(CalaWaterHeater(coordinator, heater_id, heater_data))
    
    async_add_entities(entities)


class CalaWaterHeater(CoordinatorEntity[CalaDataUpdateCoordinator], WaterHeaterEntity):
    """Representation of a Cala water heater."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_operation_list = OPERATION_LIST
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )

    def __init__(
        self,
        coordinator: CalaDataUpdateCoordinator,
        heater_id: str,
        heater_data: dict[str, Any],
    ) -> None:
        """Initialize the water heater entity."""
        super().__init__(coordinator)
        self._heater_id = heater_id
        self._attr_unique_id = f"cala_{heater_id}"
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
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._heater_data.get("topTankRawTemp")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._heater_data.get("userDesiredTemp")

    @property
    def current_operation(self) -> str:
        """Return current operation mode."""
        if self._heater_data.get("vacationMode"):
            return OPERATION_MODE_VACATION
        if self._heater_data.get("boostStatus"):
            return OPERATION_MODE_BOOST
        # Default to standard mode
        return OPERATION_MODE_STANDARD

    @property
    def is_away_mode_on(self) -> bool:
        """Return if away mode (vacation) is on."""
        return self._heater_data.get("vacationMode", False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._heater_id in self.coordinator.data
            and self._heater_data.get("cloudConnected", True)
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.coordinator.async_set_temperature(self._heater_id, temperature)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        await self.coordinator.async_set_operation_mode(self._heater_id, operation_mode)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the water heater on."""
        await self.coordinator.async_turn_on(self._heater_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the water heater off (vacation mode)."""
        await self.coordinator.async_turn_off(self._heater_id)

    async def async_turn_away_mode_on(self) -> None:
        """Turn away mode on."""
        await self.coordinator.async_set_operation_mode(
            self._heater_id, OPERATION_MODE_VACATION
        )

    async def async_turn_away_mode_off(self) -> None:
        """Turn away mode off."""
        await self.coordinator.async_set_operation_mode(
            self._heater_id, OPERATION_MODE_STANDARD
        )
