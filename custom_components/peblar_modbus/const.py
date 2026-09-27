"""Constants for the Peblar Modbus integration."""

from typing import Final

DOMAIN: Final = "peblar_modbus"

CONF_ENABLE_CONTROL: Final = "enable_control"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_UNIT_ID: Final = "unit_id"

DEFAULT_PORT: Final = 502
DEFAULT_SCAN_INTERVAL: Final = 10
DEFAULT_UNIT_ID: Final = 255

MIN_CHARGE_CURRENT: Final = 6
MAX_CHARGE_CURRENT: Final = 32

CP_STATES: Final = {
    "A": "no_ev_connected",
    "B": "suspended",
    "C": "charging",
    "D": "charging",
    "E": "error",
    "F": "fault",
    "I": "invalid",
    "U": "unknown",
}

CURRENT_LIMIT_SOURCES: Final = {
    0: "unknown",
    1: "fixed_cable",
    2: "high_temperature",
    3: "installation_limit",
    4: "dynamic_load_balancing",
    5: "group_load_balancing",
    6: "charging_cable",
    7: "overcurrent_protection",
    8: "hardware_limitation",
    9: "power_factor",
    10: "ocpp_smart_charging",
    11: "phase_imbalance",
    12: "local_scheduled_charging",
    13: "solar_charging",
    14: "current_limiter",
    15: "local_rest_api",
    16: "local_modbus_api",
    17: "external_power_limit",
    18: "household_power_limit",
    19: "reserved",
    20: "internal_power_limiter",
    21: "dynamic_rate_charging",
    22: "cpu_over_temperature",
    23: "randomized_start_delay",
    24: "mcb_trip",
}
