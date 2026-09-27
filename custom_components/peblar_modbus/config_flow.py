"""Config flow for Peblar Modbus."""

from __future__ import annotations

import logging
from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ENABLE_CONTROL,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .modbus import (
    PeblarInfo,
    PeblarModbusClient,
    PeblarModbusConnectionError,
    PeblarModbusError,
    PeblarModbusResponseError,
)

LOGGER = logging.getLogger(__name__)


class PeblarModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Peblar Modbus config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Peblar charger."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info, unit_id = await self._async_probe(
                    user_input[CONF_HOST],
                    int(user_input[CONF_PORT]),
                    int(user_input[CONF_UNIT_ID]),
                )
            except PeblarModbusConnectionError as err:
                LOGGER.warning(
                    "Cannot connect to Peblar charger at %s:%s: %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "cannot_connect"
            except PeblarModbusResponseError as err:
                LOGGER.warning(
                    "Peblar charger at %s:%s returned an invalid Modbus response: %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    err,
                )
                errors["base"] = "invalid_response"
            else:
                await self.async_set_unique_id(info.serial_number)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    }
                )
                return self.async_create_entry(
                    title=f"Peblar {info.serial_number}",
                    data={
                        **user_input,
                        CONF_PORT: int(user_input[CONF_PORT]),
                        CONF_UNIT_ID: unit_id,
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): TextSelector(TextSelectorConfig()),
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
                        NumberSelectorConfig(
                            min=1, max=65535, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=255, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5, max=300, mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(
                        CONF_ENABLE_CONTROL, default=False
                    ): BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def _async_probe(
        self, host: str, port: int, unit_id: int
    ) -> tuple[PeblarInfo, int]:
        """Probe the selected unit ID, then Peblar's other commonly used ID."""
        fallback_unit_id = 255 if unit_id == 1 else 1 if unit_id == 255 else None
        try:
            return (
                await PeblarModbusClient(host, port, unit_id).read_information(),
                unit_id,
            )
        except PeblarModbusError:
            if fallback_unit_id is None:
                raise

        LOGGER.debug(
            "Peblar charger did not respond on unit ID %s; trying %s",
            unit_id,
            fallback_unit_id,
        )
        return (
            await PeblarModbusClient(
                host, port, fallback_unit_id
            ).read_information(),
            fallback_unit_id,
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """Return the options flow."""
        return PeblarModbusOptionsFlow()


class PeblarModbusOptionsFlow(OptionsFlow):
    """Handle Peblar Modbus options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5, max=300, mode=NumberSelectorMode.BOX
                        )
                    )
                }
            ),
        )
