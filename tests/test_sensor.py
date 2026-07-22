"""Tests for the APsystems EZHI sensor platform.

This test module uses lightweight stubs for the Home Assistant runtime so it
can run in environments without homeassistant installed.
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _Entity:
    """Common base for SensorEntity and RestoreEntity so MRO resolves."""

    async def async_added_to_hass(self):
        pass

    def async_on_remove(self, func):
        return func


class _StubSensorModule(types.ModuleType):
    SensorDeviceClass = MagicMock()

    class SensorEntity(_Entity):
        pass

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        translation_key: str | None = None
        device_class: Any = None
        options: list[Any] | None = None
        native_unit_of_measurement: str | None = None
        state_class: str | None = None
        entity_category: str | None = None

    SensorStateClass = MagicMock()


class _StubConfigEntriesModule(types.ModuleType):
    ConfigEntry = object


class _StubConstModule(types.ModuleType):
    CONF_HOST = "host"
    PERCENTAGE = "%"
    Platform = MagicMock()
    UnitOfEnergy = MagicMock()
    UnitOfEnergy.KILO_WATT_HOUR = "kWh"
    UnitOfPower = MagicMock()
    UnitOfPower.WATT = "W"
    UnitOfTemperature = MagicMock()
    UnitOfTemperature.CELSIUS = "°C"


class _StubCoreModule(types.ModuleType):
    HomeAssistant = object


class _StubExceptionsModule(types.ModuleType):
    class ConfigEntryNotReady(Exception):
        pass


class _StubAiohttpClientModule(types.ModuleType):
    async def async_get_clientsession(hass):
        return MagicMock()


class _StubEntityPlatformModule(types.ModuleType):
    AddEntitiesCallback = object


class _StubRestoreStateModule(types.ModuleType):
    class RestoreEntity(_Entity):
        async def async_get_last_state(self):
            return None


class _StubCoordinatorEntity(_Entity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class _StubUpdateCoordinatorModule(types.ModuleType):
    class DataUpdateCoordinator:
        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, item):
            return cls

    class UpdateFailed(Exception):
        pass

    CoordinatorEntity = _StubCoordinatorEntity


class _StubDeviceRegistryModule(types.ModuleType):
    class DeviceInfo:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class _StubAiohttpModule(types.ModuleType):
    class ClientError(Exception):
        pass

    class ClientTimeout:
        def __init__(self, total=10):
            self.total = total

    class ClientSession:
        pass


class _StubVoluptuousModule(types.ModuleType):
    def Required(key):
        return key

    Schema = MagicMock()


def _install_stubs() -> None:
    ha = types.ModuleType("homeassistant")
    ha.components = types.ModuleType("homeassistant.components")
    ha.helpers = types.ModuleType("homeassistant.helpers")

    sensor_stub = _StubSensorModule("homeassistant.components.sensor")
    sensor_stub.SensorStateClass.MEASUREMENT = "measurement"
    sensor_stub.SensorStateClass.TOTAL_INCREASING = "total_increasing"

    const_stub = _StubConstModule("homeassistant.const")
    const_stub.Platform.SENSOR = "sensor"
    const_stub.Platform.BINARY_SENSOR = "binary_sensor"
    const_stub.Platform.NUMBER = "number"

    stubs = {
        "homeassistant": ha,
        "homeassistant.components": ha.components,
        "homeassistant.components.sensor": sensor_stub,
        "homeassistant.config_entries": _StubConfigEntriesModule(
            "homeassistant.config_entries"
        ),
        "homeassistant.const": const_stub,
        "homeassistant.core": _StubCoreModule("homeassistant.core"),
        "homeassistant.exceptions": _StubExceptionsModule("homeassistant.exceptions"),
        "homeassistant.helpers": ha.helpers,
        "homeassistant.helpers.aiohttp_client": _StubAiohttpClientModule(
            "homeassistant.helpers.aiohttp_client"
        ),
        "homeassistant.helpers.entity_platform": _StubEntityPlatformModule(
            "homeassistant.helpers.entity_platform"
        ),
        "homeassistant.helpers.restore_state": _StubRestoreStateModule(
            "homeassistant.helpers.restore_state"
        ),
        "homeassistant.helpers.update_coordinator": _StubUpdateCoordinatorModule(
            "homeassistant.helpers.update_coordinator"
        ),
        "homeassistant.helpers.device_registry": _StubDeviceRegistryModule(
            "homeassistant.helpers.device_registry"
        ),
        "aiohttp": _StubAiohttpModule("aiohttp"),
        "voluptuous": _StubVoluptuousModule("voluptuous"),
    }
    ha.components.sensor = sensor_stub
    ha.helpers.restore_state = stubs["homeassistant.helpers.restore_state"]
    ha.helpers.update_coordinator = stubs["homeassistant.helpers.update_coordinator"]
    ha.helpers.device_registry = stubs["homeassistant.helpers.device_registry"]
    ha.helpers.aiohttp_client = stubs["homeassistant.helpers.aiohttp_client"]
    ha.helpers.entity_platform = stubs["homeassistant.helpers.entity_platform"]

    sys.modules.update(stubs)


_install_stubs()

from custom_components.apsystems_ezhi.sensor import EzhiSensor, SensorStateClass


def _make_sensor(state_class: str = SensorStateClass.TOTAL_INCREASING) -> EzhiSensor:
    """Create a minimal EzhiSensor instance with a mocked coordinator."""
    coordinator = MagicMock()
    coordinator.device_info = {"deviceId": "test-device"}
    coordinator.client.host = "192.168.1.100"
    coordinator.data = MagicMock()
    coordinator.data.output = {}

    description = MagicMock()
    description.key = "pvTE"
    description.value_fn = lambda data: (
        float(data.get("pvTE")) if data.get("pvTE") is not None else None
    )
    description.state_class = state_class

    sensor = EzhiSensor(coordinator, description)
    sensor.entity_id = "sensor.test_pv_total_energy"
    return sensor


def test_first_value_sets_max():
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "12.5"}

    assert sensor.native_value == 12.5
    assert sensor._max_value == 12.5


def test_normal_increase_updates_max():
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "10.0"}
    assert sensor.native_value == 10.0

    sensor.coordinator.data.output = {"pvTE": "10.5"}
    assert sensor.native_value == 10.5
    assert sensor._max_value == 10.5


def test_decrease_is_ignored():
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "10.0"}
    assert sensor.native_value == 10.0

    sensor.coordinator.data.output = {"pvTE": "9.5"}
    assert sensor.native_value == 10.0
    assert sensor._max_value == 10.0


def test_zero_after_high_value_is_ignored():
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "100.0"}
    assert sensor.native_value == 100.0

    sensor.coordinator.data.output = {"pvTE": "0.0"}
    assert sensor.native_value == 100.0
    assert sensor._max_value == 100.0


def test_recovery_after_zero_resumes_increase():
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "100.0"}
    assert sensor.native_value == 100.0

    sensor.coordinator.data.output = {"pvTE": "0.0"}
    assert sensor.native_value == 100.0

    sensor.coordinator.data.output = {"pvTE": "100.5"}
    assert sensor.native_value == 100.5
    assert sensor._max_value == 100.5


@pytest.mark.asyncio
async def test_restore_last_state():
    sensor = _make_sensor()
    last_state = MagicMock()
    last_state.state = "55.5"

    with patch.object(
        type(sensor), "async_get_last_state", new=AsyncMock(return_value=last_state)
    ), patch.object(sensor, "async_on_remove"):
        await sensor.async_added_to_hass()

    assert sensor._max_value == 55.5

    sensor.coordinator.data.output = {"pvTE": "0.0"}
    assert sensor.native_value == 55.5


def test_non_total_increasing_sensor_not_clamped():
    sensor = _make_sensor(state_class=SensorStateClass.MEASUREMENT)
    sensor.coordinator.data.output = {"pvTE": "100.0"}
    assert sensor.native_value == 100.0

    sensor.coordinator.data.output = {"pvTE": "50.0"}
    assert sensor.native_value == 50.0
    assert sensor._max_value is None


def test_invalid_value_returns_none():
    sensor = _make_sensor()
    sensor.entity_description.value_fn = lambda data: None

    assert sensor.native_value is None


def test_logging_on_decrease(caplog):
    sensor = _make_sensor()
    sensor.coordinator.data.output = {"pvTE": "10.0"}
    sensor.native_value

    sensor.coordinator.data.output = {"pvTE": "5.0"}
    sensor.native_value

    assert "ignored decrease" in caplog.text
    assert "10.0" in caplog.text
    assert "5.0" in caplog.text


@pytest.mark.asyncio
async def test_restore_ignores_unknown_and_unavailable():
    sensor = _make_sensor()

    for bad_state in ("unknown", "unavailable", None):
        last_state = MagicMock()
        last_state.state = bad_state

        with patch.object(
            type(sensor), "async_get_last_state", new=AsyncMock(return_value=last_state)
        ), patch.object(sensor, "async_on_remove"):
            await sensor.async_added_to_hass()

        assert sensor._max_value is None


@pytest.mark.asyncio
async def test_restore_ignores_non_numeric_state():
    sensor = _make_sensor()
    last_state = MagicMock()
    last_state.state = "not-a-number"

    with patch.object(
        type(sensor), "async_get_last_state", new=AsyncMock(return_value=last_state)
    ), patch.object(sensor, "async_on_remove"):
        await sensor.async_added_to_hass()

    assert sensor._max_value is None
