"""Config flow for APsystems EZHI."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EzhiApiError, EzhiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class EzhiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for APsystems EZHI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            session = async_get_clientsession(self.hass)
            client = EzhiClient(host, session)

            try:
                info = await client.get_device_info()
            except EzhiApiError:
                errors["base"] = "cannot_connect"
            else:
                device_id = info.get("deviceId", host)
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"EZHI {device_id}", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
