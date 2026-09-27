"""Config flow for Peblar Modbus."""

from __future__ import annotations

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
from .modbus import PeblarModbusClient, PeblarModbusError


class PeblarModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Peblar Modbus config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Peblar charger."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = PeblarModbusClient(
                user_input[CONF_HOST],
                int(user_input[CONF_PORT]),
                int(user_input[CONF_UNIT_ID]),
            )
            try:
                info = await client.read_information()
            except PeblarModbusError:
                errors["base"] = "cannot_connect"
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
                        CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
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
