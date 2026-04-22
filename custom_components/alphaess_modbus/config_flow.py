from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_PORT, DEFAULT_SLAVE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .modbus_client import AlphaESSModbusClient

CONF_SLAVE_ID = "slave_id"

STEP_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
    vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE): vol.Coerce(int),
    vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.Coerce(int),
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
                connected = await client.connect()
                if not connected:
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
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )
