from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
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
