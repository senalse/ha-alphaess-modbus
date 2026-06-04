from __future__ import annotations

import re

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .config_flow import CONF_SLAVE_ID
from .const import DOMAIN, PLATFORMS
from .coordinator import AlphaESSCoordinator
from .modbus_client import AlphaESSModbusClient

SERVICE_WRITE_REGISTER = "write_register"
SERVICE_WRITE_REGISTER_SCHEMA = vol.Schema({
    vol.Required("address"): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
    vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
})

_MODEL_PREFIXES: dict[str, str] = {
    "SMILE-T10": "SMILE-T10",
    "SMILE-M5": "SMILE-M5",
    "SMILE-B3": "SMILE-B3",
    "SMILE-S5": "SMILE-S5",
    "SMILE5": "SMILE5",
    "STORION": "STORION",
    "ALD": "Alphastore",
}


def _detect_model(raw_sn: str) -> str:
    if not raw_sn:
        return "SMILE series"
    sn_upper = raw_sn.upper()
    for prefix in sorted(_MODEL_PREFIXES, key=len, reverse=True):
        if sn_upper.startswith(prefix):
            return _MODEL_PREFIXES[prefix]
    _match = re.match(r"^(.+?)(?:20\d{2}|19\d{2})", raw_sn)
    if _match:
        return _match.group(1).rstrip("-_ ").strip() or "SMILE series"
    return raw_sn[:20].strip() or "SMILE series"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.exceptions import ConfigEntryNotReady

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    client = AlphaESSModbusClient(
        host=host,
        port=port,
        slave_id=entry.data[CONF_SLAVE_ID],
    )
    try:
        await client.connect()
    except Exception as err:
        raise ConfigEntryNotReady(f"Cannot connect to {host}:{port}: {err}") from err
    if not client.connected:
        raise ConfigEntryNotReady(f"Cannot connect to {host}:{port}")

    coordinator = AlphaESSCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    raw_sn = (coordinator.data.get("inverter_sn") or "").strip().rstrip("\x00").strip()
    _model = _detect_model(raw_sn)
    _serial = raw_sn or None

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, SERVICE_WRITE_REGISTER):
        async def _handle_write_register(call: ServiceCall) -> None:
            address: int = call.data["address"]
            value: int = call.data["value"]
            # hass.data[DOMAIN] also holds non-coordinator entries (e.g. the
            # per-entry switches map), so only call coordinators.
            for obj in hass.data[DOMAIN].values():
                if isinstance(obj, AlphaESSCoordinator):
                    await obj.async_write_raw(address, value)

        hass.services.async_register(
            DOMAIN,
            SERVICE_WRITE_REGISTER,
            _handle_write_register,
            schema=SERVICE_WRITE_REGISTER_SCHEMA,
        )

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="AlphaESS Inverter",
        manufacturer="AlphaESS",
        model=_model,
        serial_number=_serial,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: AlphaESSCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        hass.data[DOMAIN].pop(f"{entry.entry_id}_switches", None)
        await coordinator.client.close()
        if not any(isinstance(o, AlphaESSCoordinator) for o in hass.data[DOMAIN].values()):
            hass.services.async_remove(DOMAIN, SERVICE_WRITE_REGISTER)
    return unloaded
