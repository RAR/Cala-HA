"""Data update coordinator for Cala water heaters."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CalaApiClient, CalaApiError, CalaAuthenticationError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CalaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching Cala water heater data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CalaApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.water_heaters: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get list of water heaters if we don't have them yet
            if not self.water_heaters:
                heaters = await self.client.get_water_heaters()
                for heater in heaters:
                    self.water_heaters[heater["id"]] = heater
            
            # Update status for each water heater
            data: dict[str, Any] = {}
            for heater_id, heater in self.water_heaters.items():
                try:
                    # Use IoT_id to query sensor data
                    iot_id = heater.get("IoT_id")
                    if not iot_id:
                        _LOGGER.warning("No IoT_id for heater %s", heater_id)
                        continue
                    
                    status = await self.client.get_water_heater_status(iot_id)
                    data[heater_id] = {
                        **heater,
                        **status,
                    }
                except CalaApiError as err:
                    _LOGGER.warning(
                        "Failed to get status for heater %s: %s", heater_id, err
                    )
                    # Keep last known data if available
                    if self.data and heater_id in self.data:
                        data[heater_id] = self.data[heater_id]
            
            return data
            
        except CalaAuthenticationError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except CalaApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_set_temperature(
        self, heater_id: str, temperature: float
    ) -> bool:
        """Set target temperature for a water heater."""
        try:
            success = await self.client.set_temperature(heater_id, temperature)
            if success:
                # Update local data immediately
                if heater_id in self.data:
                    self.data[heater_id]["userDesiredTemp"] = temperature
                await self.async_request_refresh()
            return success
        except CalaApiError as err:
            _LOGGER.error("Failed to set temperature: %s", err)
            return False

    async def async_set_operation_mode(
        self, heater_id: str, mode: str
    ) -> bool:
        """Set operation mode for a water heater."""
        try:
            success = await self.client.set_operation_mode(heater_id, mode)
            if success:
                await self.async_request_refresh()
            return success
        except CalaApiError as err:
            _LOGGER.error("Failed to set operation mode: %s", err)
            return False

    async def async_turn_on(self, heater_id: str) -> bool:
        """Turn on a water heater."""
        try:
            success = await self.client.turn_on(heater_id)
            if success:
                await self.async_request_refresh()
            return success
        except CalaApiError as err:
            _LOGGER.error("Failed to turn on water heater: %s", err)
            return False

    async def async_turn_off(self, heater_id: str) -> bool:
        """Turn off a water heater (vacation mode)."""
        try:
            success = await self.client.turn_off(heater_id)
            if success:
                await self.async_request_refresh()
            return success
        except CalaApiError as err:
            _LOGGER.error("Failed to turn off water heater: %s", err)
            return False
