"""Data update coordinator for Cala water heaters."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
        # Cache for daily usage (updated less frequently)
        self._daily_usage_cache: dict[str, dict[str, float]] = {}
        self._daily_usage_last_fetch: dict[str, datetime] = {}
        self._current_date: dict[str, datetime] = {}

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
            now = dt_util.now()
            today = now.date()
            
            for heater_id, heater in self.water_heaters.items():
                try:
                    # Use IoT_id to query sensor data
                    iot_id = heater.get("IoT_id")
                    if not iot_id:
                        _LOGGER.warning("No IoT_id for heater %s", heater_id)
                        continue
                    
                    status = await self.client.get_water_heater_status(iot_id)
                    
                    # Get daily usage from API (query historical data since midnight)
                    daily_usage = await self._get_daily_usage(heater_id, iot_id, today, now)
                    
                    # Add daily totals to the status
                    status["dailyEnergyUsed"] = daily_usage.get("dailyEnergyUsed", 0.0)
                    status["dailyWaterUsed"] = daily_usage.get("dailyWaterUsed", 0.0)
                    status["dailyResetTime"] = self._get_midnight_timestamp(today)
                    
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

    async def _get_daily_usage(
        self,
        heater_id: str,
        iot_id: str,
        today: datetime,
        now: datetime,
    ) -> dict[str, float]:
        """Get daily usage from Cala's pre-calculated summary, caching for 5 minutes."""
        # Check if we need to refresh (date changed or 5 min elapsed)
        last_fetch = self._daily_usage_last_fetch.get(heater_id)
        cached_date = self._current_date.get(heater_id)
        
        needs_refresh = (
            last_fetch is None
            or cached_date != today
            or (now - last_fetch).total_seconds() >= 300  # 5 minutes
        )
        
        if needs_refresh:
            # Format date as YYYY-MM-DD for the API
            date_str = today.strftime("%Y-%m-%d")
            
            try:
                usage = await self.client.get_daily_summary(iot_id, date_str)
                self._daily_usage_cache[heater_id] = usage
                self._daily_usage_last_fetch[heater_id] = now
                self._current_date[heater_id] = today
                _LOGGER.debug(
                    "Fetched daily summary for %s (%s): energy=%.3f kWh, water=%.1f L",
                    heater_id,
                    date_str,
                    usage.get("dailyEnergyUsed", 0),
                    usage.get("dailyWaterUsed", 0),
                )
            except CalaApiError as err:
                _LOGGER.warning("Failed to fetch daily summary: %s", err)
                # Return cached data if available
                if heater_id in self._daily_usage_cache:
                    return self._daily_usage_cache[heater_id]
                return {"dailyEnergyUsed": 0.0, "dailyWaterUsed": 0.0}
        
        return self._daily_usage_cache.get(
            heater_id, {"dailyEnergyUsed": 0.0, "dailyWaterUsed": 0.0}
        )

    def _get_midnight_timestamp(self, today: datetime) -> datetime:
        """Get the timestamp for midnight today."""
        return dt_util.start_of_local_day(
            datetime.combine(today, datetime.min.time())
        )

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
            # Get group_id and home_id from heater data
            heater = self.water_heaters.get(heater_id, {})
            group_id = heater.get("groupId")
            home_id = heater.get("homeId")
            
            success = await self.client.set_operation_mode(
                heater_id, mode, group_id=group_id, home_id=home_id
            )
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
