"""Base entity for Peblar Modbus."""

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PeblarConfigEntry, PeblarModbusCoordinator


class PeblarModbusEntity(CoordinatorEntity[PeblarModbusCoordinator]):
    """Base class for Peblar Modbus entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: PeblarConfigEntry,
        description: EntityDescription,
    ) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entity_description = description
        info = entry.runtime_data.info
        self._attr_unique_id = f"{info.serial_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{entry.data[CONF_HOST]}",
            identifiers={(DOMAIN, info.serial_number)},
            manufacturer="Peblar",
            model="Peblar EV Charger",
            model_id=info.product_number,
            name="Peblar EV Charger",
            serial_number=info.serial_number,
            sw_version=info.firmware_version,
        )
