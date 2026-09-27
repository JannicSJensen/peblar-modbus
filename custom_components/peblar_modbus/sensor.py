"""Sensors for Peblar Modbus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import CP_STATES, CURRENT_LIMIT_SOURCES
from .coordinator import PeblarConfigEntry
from .entity import PeblarModbusEntity


@dataclass(frozen=True, kw_only=True)
class PeblarSensorDescription(SensorEntityDescription):
    """Describe a Peblar sensor."""

    value_fn: Callable[[dict[str, object]], Any]
    phases_required: int = 0


SENSORS = (
    PeblarSensorDescription(
        key="cp_state",
        translation_key="cp_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(dict.fromkeys(CP_STATES.values())),
        value_fn=lambda data: CP_STATES.get(str(data["cp_state"]), "unknown"),
    ),
    PeblarSensorDescription(
        key="current_limit_source",
        translation_key="current_limit_source",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=list(CURRENT_LIMIT_SOURCES.values()),
        value_fn=lambda data: CURRENT_LIMIT_SOURCES.get(
            int(data["current_limit_source"]), "unknown"
        ),
    ),
    PeblarSensorDescription(
        key="current_limit_actual",
        translation_key="current_limit_actual",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["current_limit_actual"],
    ),
    PeblarSensorDescription(
        key="energy_session",
        translation_key="energy_session",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data["energy_session"],
    ),
    PeblarSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data["energy_total"],
    ),
    PeblarSensorDescription(
        key="power_total",
        translation_key="power_total",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["power_total"],
    ),
    PeblarSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: utcnow().replace(microsecond=0)
        - timedelta(seconds=int(data["uptime"])),
    ),
    PeblarSensorDescription(
        key="wlan_signal_strength",
        translation_key="wlan_signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["wlan_signal_strength"],
    ),
    PeblarSensorDescription(
        key="cellular_signal_strength",
        translation_key="cellular_signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["cellular_signal_strength"],
    ),
    *tuple(
        PeblarSensorDescription(
            key=f"{kind}_phase_{phase}",
            translation_key=f"{kind}_phase",
            translation_placeholders={"phase": str(phase)},
            device_class=device_class,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=unit,
            state_class=SensorStateClass.MEASUREMENT,
            phases_required=phase,
            value_fn=lambda data, key=f"{kind}_phase_{phase}": data[key],
        )
        for kind, device_class, unit in (
            ("power", SensorDeviceClass.POWER, UnitOfPower.WATT),
            ("voltage", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT),
            ("current", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE),
        )
        for phase in range(1, 4)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Peblar Modbus sensors."""
    async_add_entities(
        PeblarSensor(entry, description)
        for description in SENSORS
        if description.phases_required <= entry.runtime_data.info.phase_count
    )


class PeblarSensor(PeblarModbusEntity, SensorEntity):
    """A Peblar Modbus sensor."""

    entity_description: PeblarSensorDescription

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
