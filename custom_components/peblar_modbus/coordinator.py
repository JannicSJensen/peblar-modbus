"""Data coordinator for Peblar Modbus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .modbus import PeblarInfo, PeblarModbusClient, PeblarModbusError

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PeblarRuntimeData:
    """Runtime data for one charger."""

    coordinator: PeblarModbusCoordinator
    info: PeblarInfo
    controls_enabled: bool
    last_charge_current: float = 6


type PeblarConfigEntry = ConfigEntry[PeblarRuntimeData]


class PeblarModbusCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Poll a Peblar charger."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: PeblarModbusClient,
        info: PeblarInfo,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{info.serial_number}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.info = info

    async def _async_update_data(self) -> dict[str, object]:
        try:
            return await self.client.read_data(self.info.phase_count)
        except PeblarModbusError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_charge_current(self, value: float) -> None:
        """Set current and refresh data."""
        await self.client.set_charge_current(value)
        await self.async_request_refresh()

    async def async_set_force_single_phase(self, enabled: bool) -> None:
        """Set phase mode and refresh data."""
        await self.client.set_force_single_phase(enabled)
        await self.async_request_refresh()
