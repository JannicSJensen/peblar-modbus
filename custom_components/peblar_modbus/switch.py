"""Switch controls for Peblar Modbus."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MIN_CHARGE_CURRENT
from .coordinator import PeblarConfigEntry
from .entity import PeblarModbusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Peblar Modbus switches."""
    if not entry.runtime_data.controls_enabled:
        return
    entities: list[SwitchEntity] = [PeblarChargeSwitch(entry)]
    info = entry.runtime_data.info
    if info.independent_relays and info.phase_count > 1:
        entities.append(PeblarPhaseSwitch(entry))
    async_add_entities(entities)


class PeblarChargeSwitch(PeblarModbusEntity, SwitchEntity):
    """Pause or resume charging through the Modbus current limit."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "charge"

    def __init__(self, entry: PeblarConfigEntry) -> None:
        super().__init__(entry, EntityDescription(key="charge"))
        self._entry = entry

    @property
    def is_on(self) -> bool:
        """Return whether charging is enabled."""
        return (
            float(self.coordinator.data["charge_current_limit"])
            >= MIN_CHARGE_CURRENT
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume charging at the last requested current."""
        await self.coordinator.async_set_charge_current(
            self._entry.runtime_data.last_charge_current
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause charging."""
        current = float(self.coordinator.data["charge_current_limit"])
        if current >= MIN_CHARGE_CURRENT:
            self._entry.runtime_data.last_charge_current = current
        await self.coordinator.async_set_charge_current(0)


class PeblarPhaseSwitch(PeblarModbusEntity, SwitchEntity):
    """Control Peblar forced single-phase charging."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "force_single_phase"

    def __init__(self, entry: PeblarConfigEntry) -> None:
        super().__init__(entry, EntityDescription(key="force_single_phase"))

    @property
    def is_on(self) -> bool:
        """Return whether single-phase charging is forced."""
        return bool(self.coordinator.data["force_single_phase"])

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Force single-phase charging."""
        await self.coordinator.async_set_force_single_phase(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Allow three-phase charging."""
        await self.coordinator.async_set_force_single_phase(False)
