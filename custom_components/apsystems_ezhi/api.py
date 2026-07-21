"""Thin async client for the APsystems EZHI local HTTP API."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)


class EzhiApiError(Exception):
    """Raised when the EZHI device returns an error or an unreachable response."""


class EzhiClient:
    """Minimal client for http://{ip}/... endpoints exposed by EZHI local mode."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session

    @property
    def host(self) -> str:
        return self._host

    def _url(self, path: str) -> str:
        return f"http://{self._host}{path}"

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with self._session.get(self._url(path), timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EzhiApiError(f"Error contacting EZHI at {self._host}{path}: {err}") from err

        if payload.get("message") != "SUCCESS":
            raise EzhiApiError(f"EZHI returned failure for {path}: {payload}")

        return payload.get("data", {})

    async def get_device_info(self) -> dict[str, Any]:
        return await self._get("/getDeviceInfo")

    async def get_output_data(self) -> dict[str, Any]:
        return await self._get("/getOutputData")

    async def get_alarms(self) -> dict[str, Any]:
        return await self._get("/getAlarm")

    async def get_power(self) -> dict[str, Any]:
        return await self._get("/getPower")

    async def set_power(self, watts: int) -> dict[str, Any]:
        """Set the on-grid power limit.

        Note: this only takes effect if local mode has been enabled for the
        device in the APsystems app; otherwise the device silently ignores it.
        """
        return await self._get(f"/setPower?p={int(watts)}")
