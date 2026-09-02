"""The APsystems EZHI integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EzhiApiError, EzhiClient
from .const import DOMAIN
from .coordinator import EzhiCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]

CARD_URL = "/apsystems_ezhi/apsystems-ezhi-energy-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "apsystems-ezhi-energy-card.js"
DATA_FRONTEND_REGISTERED = "frontend_registered"


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Expose the bundled Lovelace card through Home Assistant's HTTP server."""
    from homeassistant.components.http import StaticPathConfig

    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_FRONTEND_REGISTERED):
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)]
    )
    domain_data[DATA_FRONTEND_REGISTERED] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up APsystems EZHI from a config entry."""
    await _async_register_frontend(hass)

    session = async_get_clientsession(hass)
    client = EzhiClient(entry.data[CONF_HOST], session)

    coordinator = EzhiCoordinator(hass, client)

    # Device info rarely/never changes, fetch it once up front so sensor.py
    # and the device registry entry can use it without extra polling.
    # If the device is briefly unreachable (network blip, still booting,
    # etc.), raise ConfigEntryNotReady so HA retries with backoff instead of
    # permanently failing the entry.
    try:
        coordinator.device_info = await client.get_device_info()
    except EzhiApiError as err:
        raise ConfigEntryNotReady(
            f"Could not reach EZHI device at {entry.data[CONF_HOST]}: {err}"
        ) from err

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
