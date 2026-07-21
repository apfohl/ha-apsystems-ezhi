"""Data update coordinator for APsystems EZHI."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EzhiApiError, EzhiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class EzhiData:
    """Bundle of everything the coordinator fetches each cycle."""

    output: dict[str, Any]
    alarms: dict[str, Any]
    power: dict[str, Any]


class EzhiCoordinator(DataUpdateCoordinator[EzhiData]):
    """Polls the EZHI device on a fixed interval.

    All three endpoints are cheap LAN calls, so they're fetched together each
    cycle rather than staggering intervals -- keeps things simple and avoids
    a second coordinator for what is a handful of bytes over local HTTP.
    """

    def __init__(self, hass: HomeAssistant, client: EzhiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.device_info: dict[str, Any] = {}

    async def _async_update_data(self) -> EzhiData:
        try:
            output, alarms, power = await asyncio.gather(
                self.client.get_output_data(),
                self.client.get_alarms(),
                self.client.get_power(),
            )
        except EzhiApiError as err:
            raise UpdateFailed(str(err)) from err

        return EzhiData(output=output, alarms=alarms, power=power)
