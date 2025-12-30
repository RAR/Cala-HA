"""API client for Cala Water Heater."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import base64
import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    AWS_CLIENT_ID,
    AWS_REGION,
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
        self._token_expiry: datetime | None = None

    async def authenticate(self) -> bool:
        """Authenticate with AWS Cognito using SRP."""
        try:
            # Use pycognito for SRP authentication
            from pycognito import Cognito
            
            # Run synchronous pycognito in executor
            loop = asyncio.get_event_loop()
            
            def _do_auth():
                u = Cognito(
                    AWS_USER_POOL_ID,
                    AWS_CLIENT_ID,
                    username=self._username,
                )
                u.authenticate(password=self._password)
                return u
            
            user = await loop.run_in_executor(None, _do_auth)
            
            self._access_token = user.access_token
            self._id_token = user.id_token
            self._refresh_token = user.refresh_token
            
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
            
            user = await loop.run_in_executor(None, _do_refresh)
            
            self._access_token = user.access_token
            self._id_token = user.id_token
            
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
            "Authorization": self._id_token,
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
                    headers["Authorization"] = self._id_token
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

    async def get_water_heaters(self) -> list[dict[str, Any]]:
        """Get list of water heaters for the user."""
        # Query to get user's homes and their water heaters
        query = """
            query ListWaterHeatersByHomeId($homeId: ID!) {
                listWaterHeatersByHomeId(homeId: $homeId) {
                    items {
                        id
                        iot_id
                        name
                        home_id
                        model
                        firmware_version
                    }
                }
            }
        """
        
        # First we need to get the user's home ID
        homes = await self._get_user_homes()
        
        water_heaters = []
        for home in homes:
            result = await self._graphql_request(query, {"homeId": home["id"]})
            if result.get("listWaterHeatersByHomeId", {}).get("items"):
                for heater in result["listWaterHeatersByHomeId"]["items"]:
                    heater["home_name"] = home.get("name", "Home")
                    water_heaters.append(heater)
        
        return water_heaters

    async def _get_user_homes(self) -> list[dict[str, Any]]:
        """Get user's homes."""
        query = """
            query GetUserHomes {
                getUserHomes {
                    items {
                        id
                        name
                    }
                }
            }
        """
        
        result = await self._graphql_request(query)
        return result.get("getUserHomes", {}).get("items", [])

    async def get_water_heater_status(
        self, heater_id: str
    ) -> dict[str, Any]:
        """Get current status of a water heater."""
        query = """
            query GetWaterHeaterStatus($id: ID!) {
                getWaterHeater(id: $id) {
                    id
                    iot_id
                    name
                    userDesiredTemp
                    userMaxTemp
                    topTankRawTemp
                    outletTemp
                    inletTemp
                    ambientTemp
                    averageTankTempHigh24
                    litersUsedSinceLastBoot
                    gallonsUsedSum
                    flowRate
                    socketStatus
                    cloudConnected
                    boostStatus
                    vacationMode
                    firmwareVersion
                    highEnergyUsage24
                    suctionPressure
                    deliveryPressure
                    fanPwm
                    compSpeed
                    horizonSpeed
                    panelPower
                    panelDirection
                    panelDeclination
                }
            }
        """
        
        result = await self._graphql_request(query, {"id": heater_id})
        return result.get("getWaterHeater", {})

    async def set_temperature(self, heater_id: str, temperature: float) -> bool:
        """Set the target temperature for a water heater."""
        mutation = """
            mutation SetWaterHeaterTemp($id: ID!, $temp: Float!) {
                updateWaterHeater(input: {id: $id, userDesiredTemp: $temp}) {
                    id
                    userDesiredTemp
                }
            }
        """
        
        try:
            await self._graphql_request(
                mutation, {"id": heater_id, "temp": temperature}
            )
            return True
        except CalaApiError:
            return False

    async def set_operation_mode(
        self, heater_id: str, mode: str
    ) -> bool:
        """Set the operation mode (eco, boost, vacation, etc.)."""
        # Map modes to API values
        mode_mutations = {
            "boost": """
                mutation SetBoostMode($id: ID!) {
                    updateWaterHeater(input: {id: $id, boostStatus: true}) {
                        id
                        boostStatus
                    }
                }
            """,
            "vacation": """
                mutation SetVacationMode($id: ID!) {
                    updateWaterHeater(input: {id: $id, vacationMode: true}) {
                        id
                        vacationMode
                    }
                }
            """,
            "standard": """
                mutation SetStandardMode($id: ID!) {
                    updateWaterHeater(input: {id: $id, boostStatus: false, vacationMode: false}) {
                        id
                        boostStatus
                        vacationMode
                    }
                }
            """,
        }
        
        mutation = mode_mutations.get(mode)
        if not mutation:
            _LOGGER.error("Unknown operation mode: %s", mode)
            return False
        
        try:
            await self._graphql_request(mutation, {"id": heater_id})
            return True
        except CalaApiError:
            return False

    async def turn_off(self, heater_id: str) -> bool:
        """Turn off the water heater (vacation mode)."""
        return await self.set_operation_mode(heater_id, "vacation")

    async def turn_on(self, heater_id: str) -> bool:
        """Turn on the water heater (standard mode)."""
        return await self.set_operation_mode(heater_id, "standard")
