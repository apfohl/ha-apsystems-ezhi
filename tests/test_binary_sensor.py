"""Tests for the APsystems EZHI binary-sensor (alarm) platform.

This test module uses lightweight stubs for the Home Assistant runtime so it
can run in environments without homeassistant installed.
"""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest


class _Entity:
    """Common base for BinarySensorEntity and RestoreEntity so MRO resolves."""

    async def async_added_to_hass(self):
        pass

    def async_on_remove(self, func):
        return func


class _StubBinarySensorModule(types.ModuleType):
    class BinarySensorEntity(_Entity):
        pass

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription:
        key: str
        translation_key: str | None = None
        name: str | None = None
        device_class: Any = None
        entity_category: str | None = None

    class BinarySensorDeviceClass:
        PROBLEM = "problem"


class _StubConfigEntriesModule(types.ModuleType):
    ConfigEntry = object


class _StubConstModule(types.ModuleType):
    CONF_HOST = "host"
    Platform = MagicMock()
    EntityCategory = MagicMock()


class _StubCoreModule(types.ModuleType):
    HomeAssistant = object


class _StubExceptionsModule(types.ModuleType):
    class ConfigEntryNotReady(Exception):
        pass


class _StubAiohttpClientModule(types.ModuleType):
    async def async_get_clientsession(hass):
        return MagicMock()


class _StubAiohttpModule(types.ModuleType):
    class ClientError(Exception):
        pass

    class ClientTimeout:
        def __init__(self, total=10):
            self.total = total

    class ClientSession:
        pass


class _StubEntityPlatformModule(types.ModuleType):
    AddEntitiesCallback = object


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


def _install_stubs() -> None:
    ha = types.ModuleType("homeassistant")
    ha.components = types.ModuleType("homeassistant.components")
    ha.helpers = types.ModuleType("homeassistant.helpers")

    const_stub = _StubConstModule("homeassistant.const")
    const_stub.Platform.BINARY_SENSOR = "binary_sensor"
    const_stub.EntityCategory.DIAGNOSTIC = "diagnostic"

    stubs = {
        "homeassistant": ha,
        "homeassistant.components": ha.components,
        "homeassistant.components.binary_sensor": _StubBinarySensorModule(
            "homeassistant.components.binary_sensor"
        ),
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
        "aiohttp": _StubAiohttpModule("aiohttp"),
        "homeassistant.helpers.update_coordinator": _StubUpdateCoordinatorModule(
            "homeassistant.helpers.update_coordinator"
        ),
        "homeassistant.helpers.device_registry": _StubDeviceRegistryModule(
            "homeassistant.helpers.device_registry"
        ),
    }
    ha.helpers.update_coordinator = stubs["homeassistant.helpers.update_coordinator"]
    ha.helpers.device_registry = stubs["homeassistant.helpers.device_registry"]
    ha.helpers.entity_platform = stubs["homeassistant.helpers.entity_platform"]

    sys.modules.update(stubs)


_install_stubs()

from homeassistant.const import EntityCategory

from custom_components.apsystems_ezhi.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    EzhiAlarmBinarySensor,
)
from custom_components.apsystems_ezhi.const import ALARMS


def _make_coordinator(alarms: dict[str, Any] | None = None) -> MagicMock:
    """Create a minimal mocked coordinator for alarm binary sensors."""
    coordinator = MagicMock()
    coordinator.device_info = {"deviceId": "test-device"}
    coordinator.client.host = "192.168.1.100"
    coordinator.data = MagicMock()
    coordinator.data.alarms = alarms if alarms is not None else {}
    return coordinator


def test_all_alarm_keys_have_a_description():
    keys = {description.key for description in BINARY_SENSOR_DESCRIPTIONS}
    assert keys == set(ALARMS)


def test_alarm_descriptions_use_problem_device_class():
    for description in BINARY_SENSOR_DESCRIPTIONS:
        assert description.device_class == "problem"
        assert description.entity_category is EntityCategory.DIAGNOSTIC


def test_alarm_is_off_when_value_is_zero():
    coordinator = _make_coordinator(alarms={"BatHTP": "0"})
    description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "BatHTP")
    sensor = EzhiAlarmBinarySensor(coordinator, description)

    assert sensor.is_on is False


def test_alarm_is_on_when_value_is_non_zero():
    coordinator = _make_coordinator(alarms={"BatHTP": "1"})
    description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "BatHTP")
    sensor = EzhiAlarmBinarySensor(coordinator, description)

    assert sensor.is_on is True


def test_alarm_is_on_for_any_non_zero_string():
    for value in ("2", "255", "ERROR", "active"):
        coordinator = _make_coordinator(alarms={"BatCE": value})
        description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "BatCE")
        sensor = EzhiAlarmBinarySensor(coordinator, description)

        assert sensor.is_on is True, f"expected True for alarm value {value!r}"


def test_alarm_is_none_when_key_missing():
    coordinator = _make_coordinator(alarms={})
    description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "BCI")
    sensor = EzhiAlarmBinarySensor(coordinator, description)

    assert sensor.is_on is None


def test_entity_unique_id_uses_device_id_and_key():
    coordinator = _make_coordinator(alarms={"VRP": "0"})
    description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "VRP")
    sensor = EzhiAlarmBinarySensor(coordinator, description)

    assert sensor._attr_unique_id == "test-device_VRP"


def test_entity_device_info_is_populated():
    coordinator = _make_coordinator(alarms={"BCC": "0"})
    description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == "BCC")
    sensor = EzhiAlarmBinarySensor(coordinator, description)

    device_info = sensor._attr_device_info
    assert device_info.name == "APsystems EZHI test-device"
    assert device_info.manufacturer == "APsystems"
    assert device_info.model == "EZHI"
