"""Binary sensor platform for APsystems EZHI alarms."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ALARMS, DOMAIN
from .coordinator import EzhiCoordinator, EzhiData
from .entity import EzhiEntity

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = tuple(
    BinarySensorEntityDescription(
        key=key,
        translation_key=f"alarm_{key.lower()}",
        name=name,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category="diagnostic",
    )
    for key, name in ALARMS.items()
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up EZHI alarm binary sensors from a config entry."""
    coordinator: EzhiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EzhiAlarmBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class EzhiAlarmBinarySensor(EzhiEntity, BinarySensorEntity):
    """True (problem) whenever the alarm flag is not '0'."""

    def __init__(
        self, coordinator: EzhiCoordinator, description: BinarySensorEntityDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        data: EzhiData = self.coordinator.data
        raw = data.alarms.get(self.entity_description.key)
        if raw is None:
            return None
        return str(raw) != "0"
