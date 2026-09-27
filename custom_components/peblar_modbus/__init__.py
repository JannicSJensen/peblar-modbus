"""Peblar Modbus integration."""

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_ENABLE_CONTROL,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
)
from .coordinator import (
    PeblarConfigEntry,
    PeblarModbusCoordinator,
    PeblarRuntimeData,
)
from .modbus import PeblarModbusClient, PeblarModbusError

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: PeblarConfigEntry) -> bool:
    """Set up Peblar Modbus from a config entry."""
    client = PeblarModbusClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
    )
    try:
        info = await client.read_information()
    except PeblarModbusError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = PeblarModbusCoordinator(
        hass,
        entry,
        client,
        info,
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    current = coordinator.data.get("charge_current_limit", 0)
    entry.runtime_data = PeblarRuntimeData(
        coordinator=coordinator,
        info=info,
        controls_enabled=entry.data.get(CONF_ENABLE_CONTROL, False),
        last_charge_current=float(current) if float(current) >= 6 else 6,
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PeblarConfigEntry) -> bool:
    """Unload a Peblar Modbus config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: PeblarConfigEntry
) -> None:
    """Reload after config entry options change."""
    await hass.config_entries.async_reload(entry.entry_id)
