"""Number platform: on-grid power setpoint for APsystems EZHI."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_ON_GRID_POWER, MIN_ON_GRID_POWER
from .coordinator import EzhiCoordinator, EzhiData
from .entity import EzhiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the on-grid power number entity from a config entry."""
    coordinator: EzhiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EzhiOnGridPowerNumber(coordinator)])


class EzhiOnGridPowerNumber(EzhiEntity, NumberEntity):
    """Lets you read/set the on-grid power limit (setPower?p=...).

    Note: per the EZHI local API docs, writes only take effect once local
    mode has been enabled for the device in the APsystems app. Without that,
    the device accepts the call but silently ignores the new value.
    """

    _attr_translation_key = "on_grid_power_limit"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = MIN_ON_GRID_POWER
    _attr_native_max_value = MAX_ON_GRID_POWER
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: EzhiCoordinator) -> None:
        super().__init__(coordinator, "on_grid_power_limit")

    @property
    def native_value(self) -> float | None:
        data: EzhiData = self.coordinator.data
        raw = data.power.get("power")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_power(int(value))
        await self.coordinator.async_request_refresh()
