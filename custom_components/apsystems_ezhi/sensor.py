"""Sensor platform for APsystems EZHI."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BATTERY_STATUS, DOMAIN
from .coordinator import EzhiCoordinator, EzhiData
from .entity import EzhiEntity


@dataclass(frozen=True, kw_only=True)
class EzhiSensorDescription(SensorEntityDescription):
    """Adds a value_fn that pulls a field out of the coordinator's output data."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None


def _num(key: str) -> Callable[[dict[str, Any]], float | None]:
    """Build a value_fn that pulls a numeric field out of getOutputData."""

    def _get(data: dict[str, Any]) -> float | None:
        raw = data.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    return _get


SENSOR_DESCRIPTIONS: tuple[EzhiSensorDescription, ...] = (
    EzhiSensorDescription(
        key="batS",
        translation_key="battery_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(BATTERY_STATUS.values()),
        value_fn=lambda d: BATTERY_STATUS.get(str(d.get("batS")), "unknown"),
    ),
    EzhiSensorDescription(
        key="batSoc",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("batSoc"),
    ),
    EzhiSensorDescription(
        key="batSoh",
        translation_key="battery_soh",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        value_fn=_num("batSoh"),
    ),
    EzhiSensorDescription(
        key="batTemp",
        translation_key="battery_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("batTemp"),
    ),
    EzhiSensorDescription(
        key="devTemp",
        translation_key="device_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        value_fn=_num("devTemp"),
    ),
    EzhiSensorDescription(
        key="pvP",
        translation_key="pv_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("pvP"),
    ),
    EzhiSensorDescription(
        key="pvTE",
        translation_key="pv_total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("pvTE"),
    ),
    EzhiSensorDescription(
        key="batP",
        translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("batP"),
    ),
    EzhiSensorDescription(
        key="batCTE",
        translation_key="battery_charge_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("batCTE"),
    ),
    EzhiSensorDescription(
        key="batDTE",
        translation_key="battery_discharge_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("batDTE"),
    ),
    EzhiSensorDescription(
        key="ogP",
        translation_key="on_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("ogP"),
    ),
    EzhiSensorDescription(
        key="ogOTE",
        translation_key="on_grid_output_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("ogOTE"),
    ),
    EzhiSensorDescription(
        key="ogITE",
        translation_key="on_grid_input_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("ogITE"),
    ),
    EzhiSensorDescription(
        key="ofgP",
        translation_key="off_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_num("ofgP"),
    ),
    EzhiSensorDescription(
        key="ofgOTE",
        translation_key="off_grid_output_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("ofgOTE"),
    ),
    EzhiSensorDescription(
        key="ofgITE",
        translation_key="off_grid_input_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_num("ofgITE"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up EZHI sensors from a config entry."""
    coordinator: EzhiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EzhiSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class EzhiSensor(EzhiEntity, SensorEntity):
    """A single field pulled from getOutputData."""

    entity_description: EzhiSensorDescription

    def __init__(self, coordinator: EzhiCoordinator, description: EzhiSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._last_value: float | None = None
        self._pending_value: float | None = None
        self._pending_count = 0

    @property
    def native_value(self) -> Any:
        data: EzhiData = self.coordinator.data
        if self.entity_description.value_fn is None:
            return None
        value = self.entity_description.value_fn(data.output)

        if self.entity_description.state_class != SensorStateClass.TOTAL_INCREASING or value is None:
            return value

        return self._debounced_total(value)

    def _debounced_total(self, value: float) -> float:
        """Guard total_increasing counters against transient bad readings.

        The device has been observed to briefly report 0 right after coming
        back from being unreachable (e.g. overnight WiFi drop), before
        correcting itself a poll later once it reloads its persisted total.
        A single lower reading is therefore treated as suspect rather than
        a genuine counter reset; it only gets accepted once it repeats a
        few polls in a row, which is what a real reset (or firmware update)
        would look like.
        """
        if self._last_value is None or value >= self._last_value:
            self._last_value = value
            self._pending_value = None
            self._pending_count = 0
            return value

        if self._pending_value == value:
            self._pending_count += 1
        else:
            self._pending_value = value
            self._pending_count = 1

        if self._pending_count >= 3:
            self._last_value = value
            self._pending_value = None
            self._pending_count = 0
            return value

        # Not confirmed yet -- hold the last known good value.
        return self._last_value
