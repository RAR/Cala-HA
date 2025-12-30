"""Config flow for Cala Water Heater integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class CalaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cala Water Heater."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Import here to avoid circular imports
            from .api import CalaApiClient

            try:
                session = async_get_clientsession(self.hass)
                client = CalaApiClient(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )

                # Try to authenticate
                if await client.authenticate():
                    # Check for existing entries with same username
                    await self.async_set_unique_id(user_input[CONF_USERNAME])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Cala ({user_input[CONF_USERNAME]})",
                        data=user_input,
                    )
                else:
                    errors["base"] = "invalid_auth"

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during authentication")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthorization."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            from .api import CalaApiClient

            entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )
            assert entry is not None

            try:
                session = async_get_clientsession(self.hass)
                client = CalaApiClient(
                    username=entry.data[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )

                if await client.authenticate():
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
                else:
                    errors["base"] = "invalid_auth"

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
