"""Base entity shared by all EZHI platforms."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EzhiCoordinator


class EzhiEntity(CoordinatorEntity[EzhiCoordinator]):
    """Common base: wires up device_info and a stable unique_id prefix."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EzhiCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.device_info
        device_id = info.get("deviceId", coordinator.client.host)

        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"APsystems EZHI {device_id}",
            manufacturer="APsystems",
            model=info.get("type", "EZHI"),
            sw_version=info.get("devVer"),
            configuration_url=f"http://{coordinator.client.host}",
        )
