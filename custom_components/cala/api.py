"""API client for Cala Water Heater."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    AWS_CLIENT_ID,
    AWS_USER_POOL_ID,
    GRAPHQL_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class CalaAuthenticationError(Exception):
    """Exception for authentication errors."""


class CalaApiError(Exception):
    """Exception for API errors."""


class CalaApiClient:
    """API client for Cala water heaters using AWS Cognito and AppSync GraphQL."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._access_token: str | None = None
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._cognito = None

    async def authenticate(self) -> bool:
        """Authenticate with AWS Cognito using SRP."""
        try:
            from pycognito import Cognito

            loop = asyncio.get_event_loop()

            def _do_auth():
                u = Cognito(
                    AWS_USER_POOL_ID,
                    AWS_CLIENT_ID,
                    username=self._username,
                )
                u.authenticate(password=self._password)
                return u

            self._cognito = await loop.run_in_executor(None, _do_auth)

            self._access_token = self._cognito.access_token
            self._id_token = self._cognito.id_token
            self._refresh_token = self._cognito.refresh_token

            _LOGGER.debug("Successfully authenticated with Cognito")
            return True

        except Exception as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise CalaAuthenticationError(f"Authentication failed: {err}") from err

    async def _refresh_tokens(self) -> None:
        """Refresh access tokens if expired."""
        if not self._refresh_token:
            await self.authenticate()
            return

        try:
            from pycognito import Cognito

            loop = asyncio.get_event_loop()

            def _do_refresh():
                u = Cognito(
                    AWS_USER_POOL_ID,
                    AWS_CLIENT_ID,
                    username=self._username,
                    id_token=self._id_token,
                    access_token=self._access_token,
                    refresh_token=self._refresh_token,
                )
                u.renew_access_token()
                return u

            self._cognito = await loop.run_in_executor(None, _do_refresh)

            self._access_token = self._cognito.access_token
            self._id_token = self._cognito.id_token

            _LOGGER.debug("Successfully refreshed tokens")

        except Exception as err:
            _LOGGER.warning("Token refresh failed, re-authenticating: %s", err)
            await self.authenticate()

    async def _ensure_authenticated(self) -> None:
        """Ensure we have valid authentication tokens."""
        if not self._access_token:
            await self.authenticate()

    async def _graphql_request(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GraphQL request to the AppSync endpoint."""
        await self._ensure_authenticated()

        headers = {
            "Content-Type": "application/json",
            "Authorization": self._access_token,
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            async with self._session.post(
                GRAPHQL_ENDPOINT,
                json=payload,
                headers=headers,
            ) as response:
                if response.status == 401:
                    # Token expired, refresh and retry
                    await self._refresh_tokens()
                    headers["Authorization"] = self._access_token
                    async with self._session.post(
                        GRAPHQL_ENDPOINT,
                        json=payload,
                        headers=headers,
                    ) as retry_response:
                        data = await retry_response.json()
                else:
                    data = await response.json()

                if "errors" in data:
                    _LOGGER.error("GraphQL errors: %s", data["errors"])
                    raise CalaApiError(f"GraphQL error: {data['errors']}")

                return data.get("data", {})

        except aiohttp.ClientError as err:
            _LOGGER.error("API request failed: %s", err)
            raise CalaApiError(f"API request failed: {err}") from err

    async def get_homes(self) -> list[dict[str, Any]]:
        """Get user's homes."""
        query = """
            query ListHomes {
                listHomes {
                    items {
                        id
                        name
                        address1
                        city
                        state
                        zip
                        latitude
                        longitude
                        timezoneOffset
                        energyRegion
                        groupId
                    }
                }
            }
        """

        result = await self._graphql_request(query)
        return result.get("listHomes", {}).get("items", [])

    async def get_water_heaters(self, home_id: str | None = None) -> list[dict[str, Any]]:
        """Get list of water heaters for the user."""
        if home_id:
            return await self._get_water_heaters_by_home(home_id)

        # Get all homes and their water heaters
        homes = await self.get_homes()
        water_heaters = []

        for home in homes:
            heaters = await self._get_water_heaters_by_home(home["id"])
            for heater in heaters:
                heater["home_name"] = home.get("name", "Home")
                heater["home_id"] = home["id"]
                water_heaters.append(heater)

        return water_heaters

    async def _get_water_heaters_by_home(self, home_id: str) -> list[dict[str, Any]]:
        """Get water heaters for a specific home."""
        query = """
            query ListWaterHeaterByHomeId($homeId: ID!) {
                listWaterHeaterByHomeId(homeId: $homeId) {
                    items {
                        id
                        name
                        IoT_id
                        status
                        homeId
                        groupId
                        createdAt
                        updatedAt
                    }
                }
            }
        """

        result = await self._graphql_request(query, {"homeId": home_id})
        return result.get("listWaterHeaterByHomeId", {}).get("items", [])

    async def get_water_heater_status(self, device_id: str) -> dict[str, Any]:
        """Get current status of a water heater by IoT_id (deviceId)."""
        # Get the latest bucketed sensor data (aggregated)
        bucketed_query = """
            query GetLatestBucketedSensorData($deviceId: String!) {
                listBucketedSensorDataByDeviceIdAndTimestamp(
                    deviceId: $deviceId,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        deviceId
                        timestamp
                        ambientTemp
                        ambientHumidity
                        litersUsed
                        lowerTankTemp
                        outletTemp
                        topTankTemp
                        upperTankTemp
                        energyUsed
                        hotLiters
                        uptime
                        tankGradient
                        inletTemp
                        plannerRestartCount
                        maxDeliveryTemp
                        userMaxTemp
                        userDesiredTemp
                        safetyLockout
                        compressorBackoff
                        compressorLock
                    }
                }
            }
        """

        # Get the latest raw sensor data (real-time temps and compressor info)
        raw_query = """
            query GetLatestRawSensorData($deviceId: String!) {
                listSensorDataByDeviceIdAndTimestamp(
                    deviceId: $deviceId,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        topTankTemp
                        upperTankTemp
                        lowerTankTemp
                        outletTemp
                        ambientTemp
                        compRunning
                        compFreq
                        deliveryTemp
                        deliveryPressure
                        suctionPressure
                        fanPwr
                    }
                }
            }
        """

        # Fetch both in parallel would be nice, but for simplicity do sequentially
        bucketed_result = await self._graphql_request(bucketed_query, {"deviceId": device_id})
        bucketed_items = bucketed_result.get("listBucketedSensorDataByDeviceIdAndTimestamp", {}).get("items", [])

        raw_result = await self._graphql_request(raw_query, {"deviceId": device_id})
        raw_items = raw_result.get("listSensorDataByDeviceIdAndTimestamp", {}).get("items", [])

        # Merge the results
        data: dict[str, Any] = {}
        if bucketed_items:
            data.update(bucketed_items[0])
        if raw_items:
            data.update(raw_items[0])

        return data

    async def get_device_properties(self, device_id: str) -> dict[str, Any]:
        """Get device properties (firmware, network mode, etc.)."""
        query = """
            query GetLatestDeviceProperties($deviceId: String!) {
                listDevicePropertiesByDeviceIdAndTimestamp(
                    deviceId: $deviceId,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        deviceId
                        timestamp
                        firmwareVersion
                        efrFirmwareVersion
                        timezoneOffset
                        networkMode
                        reactiveCapacity
                        sidewalkAvailable
                    }
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id})
        items = result.get("listDevicePropertiesByDeviceIdAndTimestamp", {}).get("items", [])

        if items:
            return items[0]
        return {}

    async def get_controls(self, device_id: str) -> dict[str, Any]:
        """Get current control settings."""
        query = """
            query GetLatestControls($deviceId: String!) {
                listControlsByDeviceIdAndTimestamp(
                    deviceId: $deviceId,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        deviceId
                        timestamp
                        type
                        upperSetPoint
                        lowerSetPoint
                        upperElement
                        lowerElement
                        compSpeed
                        compAccel
                        shutoffTemp
                    }
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id})
        items = result.get("listControlsByDeviceIdAndTimestamp", {}).get("items", [])

        if items:
            return items[0]
        return {}

    async def get_monitoring_alerts(self, device_id: str) -> dict[str, Any]:
        """Get latest monitoring alerts."""
        query = """
            query GetLatestMonitoringAlert($deviceId: ID!) {
                getLatestMonitoringAlert(deviceId: $deviceId) {
                    deviceId
                    timestamp
                    lowGallonAvailability
                    highEnergyUsage24
                    highWaterUsage24
                    lowEnergyUsage24
                    lowerWaterUsage24
                    averageTankTempHigh24
                    lowerTankNeverWarm24
                    topTankTempLow3Readings
                    lowFlowWithTempDrop
                    constantlyLowTank
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id})
        return result.get("getLatestMonitoringAlert") or {}

    async def get_rolling_state(self, device_id: str) -> dict[str, Any]:
        """Get rolling device state (24h rolling averages)."""
        query = """
            query GetRollingDeviceState($deviceId: ID!) {
                getRollingDeviceState(deviceId: $deviceId) {
                    deviceId
                    rbIndex
                    lastWriteAt
                    updatedAt
                    energyRB
                    waterRB
                    topTankTempRB
                    upperTankTempRB
                    lowerTankTempRB
                    ambientTempRB
                    ambientHumidityRB
                    averageTankTempRB
                    litersAvailableRB
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id})
        return result.get("getRollingDeviceState") or {}

    async def get_boost_mode(self, water_heater_id: str) -> dict[str, Any] | None:
        """Get active boost mode for a water heater."""
        # Get current time as epoch
        now = int(datetime.now().timestamp())
        
        query = """
            query GetActiveBoostMode($waterHeaterId: ID!, $endDate: ModelIntKeyConditionInput) {
                listBoostModeByWaterHeaterIdAndEndDate(
                    waterHeaterId: $waterHeaterId,
                    endDate: $endDate,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        id
                        waterHeaterId
                        startDate
                        endDate
                        targetTemp
                        active
                    }
                }
            }
        """

        result = await self._graphql_request(query, {
            "waterHeaterId": water_heater_id,
            "endDate": {"ge": now}
        })
        items = result.get("listBoostModeByWaterHeaterIdAndEndDate", {}).get("items", [])

        if items:
            return items[0]
        return None

    async def get_vacation_mode(self, home_id: str) -> dict[str, Any] | None:
        """Get active vacation mode for a home."""
        now = int(datetime.now().timestamp())
        
        query = """
            query GetActiveVacation($homeId: ID!, $startDate: ModelIntKeyConditionInput) {
                listVacationByHomeIdAndStartDate(
                    homeId: $homeId,
                    startDate: $startDate,
                    sortDirection: DESC,
                    limit: 1
                ) {
                    items {
                        id
                        homeId
                        startDate
                        endDate
                        active
                    }
                }
            }
        """

        result = await self._graphql_request(query, {
            "homeId": home_id,
            "startDate": {"le": now}
        })
        items = result.get("listVacationByHomeIdAndStartDate", {}).get("items", [])

        # Check if vacation is currently active
        if items:
            vacation = items[0]
            if vacation.get("endDate", 0) > now:
                return vacation
        return None

    async def get_full_status(self, water_heater: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive status combining all data sources."""
        device_id = water_heater.get("IoT_id")
        heater_id = water_heater.get("id")
        home_id = water_heater.get("homeId")

        if not device_id:
            _LOGGER.warning("Water heater missing IoT_id: %s", water_heater)
            return {}

        # Fetch all data in parallel
        sensor_task = self.get_water_heater_status(device_id)
        props_task = self.get_device_properties(device_id)
        controls_task = self.get_controls(device_id)
        alerts_task = self.get_monitoring_alerts(device_id)
        rolling_task = self.get_rolling_state(device_id)
        boost_task = self.get_boost_mode(heater_id) if heater_id else asyncio.sleep(0)
        vacation_task = self.get_vacation_mode(home_id) if home_id else asyncio.sleep(0)

        results = await asyncio.gather(
            sensor_task,
            props_task,
            controls_task,
            alerts_task,
            rolling_task,
            boost_task,
            vacation_task,
            return_exceptions=True,
        )

        sensor_data, props, controls, alerts, rolling, boost, vacation = results

        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _LOGGER.warning("Failed to fetch data part %d: %s", i, result)

        sensor_data = sensor_data if not isinstance(sensor_data, Exception) else {}
        props = props if not isinstance(props, Exception) else {}
        controls = controls if not isinstance(controls, Exception) else {}
        alerts = alerts if not isinstance(alerts, Exception) else {}
        rolling = rolling if not isinstance(rolling, Exception) else {}
        boost = boost if not isinstance(boost, Exception) else None
        vacation = vacation if not isinstance(vacation, Exception) else None

        return {
            "water_heater": water_heater,
            "sensor_data": sensor_data,
            "device_properties": props,
            "controls": controls,
            "alerts": alerts,
            "rolling_state": rolling,
            "boost_mode": boost,
            "vacation_mode": vacation,
            "is_boost_active": bool(boost and boost.get("active")),
            "is_vacation_active": bool(vacation),
        }

    async def set_temperature(self, water_heater_id: str, temperature: float) -> bool:
        """Set the target temperature for a water heater."""
        mutation = """
            mutation UpdateWaterHeaterTemp($input: UpdateWaterHeaterInput!) {
                updateWaterHeater(input: $input) {
                    id
                }
            }
        """

        try:
            await self._graphql_request(
                mutation,
                {"input": {"id": water_heater_id, "userDesiredTemp": temperature}}
            )
            return True
        except CalaApiError as err:
            _LOGGER.error("Failed to set temperature: %s", err)
            return False

    async def create_boost_mode(
        self,
        water_heater_id: str,
        target_temp: float,
        duration_minutes: int = 60,
        group_id: str | None = None,
    ) -> bool:
        """Create a boost mode session."""
        now = int(datetime.now().timestamp())
        end_time = now + (duration_minutes * 60)

        mutation = """
            mutation CreateBoostMode($input: CreateBoostModeInput!) {
                createBoostMode(input: $input) {
                    id
                }
            }
        """

        try:
            await self._graphql_request(
                mutation,
                {
                    "input": {
                        "waterHeaterId": water_heater_id,
                        "startDate": now,
                        "endDate": end_time,
                        "targetTemp": target_temp,
                        "active": True,
                        "groupId": group_id,
                    }
                }
            )
            return True
        except CalaApiError as err:
            _LOGGER.error("Failed to create boost mode: %s", err)
            return False

    async def cancel_boost_mode(self, boost_id: str) -> bool:
        """Cancel an active boost mode."""
        mutation = """
            mutation UpdateBoostMode($input: UpdateBoostModeInput!) {
                updateBoostMode(input: $input) {
                    id
                }
            }
        """

        try:
            await self._graphql_request(
                mutation,
                {"input": {"id": boost_id, "active": False}}
            )
            return True
        except CalaApiError as err:
            _LOGGER.error("Failed to cancel boost mode: %s", err)
            return False

    async def create_vacation_mode(
        self,
        home_id: str,
        start_date: int,
        end_date: int,
        group_id: str | None = None,
    ) -> bool:
        """Create a vacation mode."""
        mutation = """
            mutation CreateVacation($input: CreateVacationInput!) {
                createVacation(input: $input) {
                    id
                }
            }
        """

        try:
            await self._graphql_request(
                mutation,
                {
                    "input": {
                        "homeId": home_id,
                        "startDate": start_date,
                        "endDate": end_date,
                        "active": True,
                        "groupId": group_id,
                    }
                }
            )
            return True
        except CalaApiError as err:
            _LOGGER.error("Failed to create vacation mode: %s", err)
            return False

    async def cancel_vacation_mode(self, vacation_id: str) -> bool:
        """Cancel an active vacation mode."""
        mutation = """
            mutation UpdateVacation($input: UpdateVacationInput!) {
                updateVacation(input: $input) {
                    id
                }
            }
        """

        try:
            await self._graphql_request(
                mutation,
                {"input": {"id": vacation_id, "active": False}}
            )
            return True
        except CalaApiError as err:
            _LOGGER.error("Failed to cancel vacation mode: %s", err)
            return False

    async def get_daily_summary(self, device_id: str, date: str) -> dict[str, Any]:
        """Get daily device summary (date format: YYYY-MM-DD)."""
        query = """
            query GetDailyDeviceSummary($deviceId: ID!, $date: String!) {
                getDailyDeviceSummary(deviceId: $deviceId, date: $date) {
                    deviceId
                    date
                    energyUsed
                    waterUsed
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id, "date": date})
        return result.get("getDailyDeviceSummary") or {}

    async def get_energy_usage_history(
        self, device_id: str, limit: int = 7
    ) -> list[dict[str, Any]]:
        """Get recent daily energy usage."""
        query = """
            query GetDailySummaries($deviceId: ID!) {
                listDailyDeviceSummaryByDeviceIdAndDate(
                    deviceId: $deviceId,
                    sortDirection: DESC,
                    limit: 7
                ) {
                    items {
                        deviceId
                        date
                        energyUsed
                        waterUsed
                    }
                }
            }
        """

        result = await self._graphql_request(query, {"deviceId": device_id})
        return result.get("listDailyDeviceSummaryByDeviceIdAndDate", {}).get("items", [])
