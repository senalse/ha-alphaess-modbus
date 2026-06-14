from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
try:
    from homeassistant.config_entries import ConfigFlowResult as FlowResult
except ImportError:
    from homeassistant.data_entry_flow import FlowResult  # HA < 2024.4

from .const import DEFAULT_PORT, DEFAULT_SLAVE, DOMAIN
from .modbus_client import AlphaESSModbusClient

_LOGGER = logging.getLogger(__name__)

CONF_SLAVE_ID = "slave_id"

STEP_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
    vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE): vol.Coerce(int),
})


class AlphaESSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> AlphaESSOptionsFlowHandler:
        return AlphaESSOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AlphaESSModbusClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                slave_id=user_input[CONF_SLAVE_ID],
            )
            try:
                await client.connect()
                if not client.connected:
                    errors["base"] = "cannot_connect"
                else:
                    await client.read_register(0x0102, "int16")  # SoC register
                    await client.close()
                    await self.async_set_unique_id(
                        f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"AlphaESS ({user_input[CONF_HOST]})",
                        data=user_input,
                    )
            except Exception:
                _LOGGER.exception("AlphaESS connection test failed for %s:%s slave=%s",
                                  user_input[CONF_HOST], user_input[CONF_PORT],
                                  user_input[CONF_SLAVE_ID])
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict | None = None) -> FlowResult:
        try:
            entry = self._get_reconfigure_entry()
        except AttributeError:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AlphaESSModbusClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                slave_id=user_input[CONF_SLAVE_ID],
            )
            try:
                await client.connect()
                if not client.connected:
                    errors["base"] = "cannot_connect"
                else:
                    await client.read_register(0x0102, "int16")
                    await client.close()
                    self.hass.config_entries.async_update_entry(entry, data={**entry.data, **user_input})
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")
            except Exception:
                _LOGGER.exception("AlphaESS connection test failed for %s:%s slave=%s",
                                  user_input[CONF_HOST], user_input[CONF_PORT],
                                  user_input[CONF_SLAVE_ID])
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=entry.data.get(CONF_PORT, DEFAULT_PORT)): vol.Coerce(int),
                vol.Required(CONF_SLAVE_ID, default=entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE)): vol.Coerce(int),
            }),
            errors=errors,
        )


class AlphaESSOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        poll_mode = options.get("poll_mode", "normal")
        slow_multiplier = options.get("slow_multiplier", 3.0)
        fast_multiplier = options.get("fast_multiplier", 0.5)
        model_variant = options.get("model_variant", "standard")

        schema = vol.Schema({
            vol.Required("poll_mode", default=poll_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "slow",   "label": "Slow"},
                        {"value": "normal", "label": "Normal"},
                        {"value": "fast",   "label": "Fast"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required("slow_multiplier", default=float(slow_multiplier)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.25, max=10.0, step=0.25,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required("fast_multiplier", default=float(fast_multiplier)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=10.0, step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required("model_variant", default=model_variant): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "standard", "label": "Standard"},
                        {"value": "b3",       "label": "SMILE-B3 / SMILE-B3-PLUS"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
