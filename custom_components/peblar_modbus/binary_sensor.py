"""Binary sensors for Peblar Modbus."""

from dataclasses import dataclass
from typing import cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PeblarConfigEntry
from .entity import PeblarModbusEntity


@dataclass(frozen=True, kw_only=True)
class PeblarBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Peblar binary sensor."""

    data_key: str


BINARY_SENSORS = (
    PeblarBinarySensorDescription(
        key="problem",
        translation_key="problem",
        data_key="errors",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PeblarBinarySensorDescription(
        key="warning",
        translation_key="warning",
        data_key="warnings",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PeblarBinarySensorDescription(
        key="socket_lock",
        translation_key="socket_lock",
        data_key="lock_state",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Peblar Modbus binary sensors."""
    async_add_entities(
        PeblarBinarySensor(entry, description) for description in BINARY_SENSORS
    )


class PeblarBinarySensor(PeblarModbusEntity, BinarySensorEntity):
    """A Peblar Modbus binary sensor."""

    entity_description: PeblarBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return the binary sensor state."""
        return bool(self.coordinator.data[self.entity_description.data_key])

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose active warning or error codes."""
        value = self.coordinator.data[self.entity_description.data_key]
        if not isinstance(value, tuple):
            return None
        return {"codes": cast(tuple[int, ...], value)}
