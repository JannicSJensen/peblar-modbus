"""Number controls for Peblar Modbus."""

from homeassistant.components.number import NumberDeviceClass, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_CHARGE_CURRENT, MIN_CHARGE_CURRENT
from .coordinator import PeblarConfigEntry
from .entity import PeblarModbusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Peblar Modbus number controls."""
    if entry.runtime_data.controls_enabled:
        async_add_entities([PeblarChargeCurrentNumber(entry)])


class PeblarChargeCurrentNumber(PeblarModbusEntity, RestoreNumber):
    """Control the requested charge current."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_CHARGE_CURRENT
    _attr_native_max_value = MAX_CHARGE_CURRENT
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_translation_key = "charge_current_limit"

    def __init__(self, entry: PeblarConfigEntry) -> None:
        super().__init__(entry, EntityDescription(key="charge_current_limit"))
        self._entry = entry

    @property
    def native_value(self) -> float:
        """Return the selected non-zero charge current."""
        current = float(self.coordinator.data["charge_current_limit"])
        if current >= MIN_CHARGE_CURRENT:
            self._entry.runtime_data.last_charge_current = current
        return self._entry.runtime_data.last_charge_current

    async def async_set_native_value(self, value: float) -> None:
        """Set the charge current, or remember it while charging is paused."""
        self._entry.runtime_data.last_charge_current = value
        if float(self.coordinator.data["charge_current_limit"]) >= MIN_CHARGE_CURRENT:
            await self.coordinator.async_set_charge_current(value)
        else:
            self.async_write_ha_state()
