from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, SELECT_REGISTERS, ModbusSelectDef
from .coordinator import AlphaESSCoordinator

# inverter_ac_limit has no Modbus address — it's a local config value used by
# the excess export switch to calculate dispatch power.
LOCAL_ONLY_SELECTS = {"inverter_ac_limit"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AlphaESSSelect(coordinator, entry, reg)
        for reg in SELECT_REGISTERS
    )


class AlphaESSSelect(RestoreEntity, SelectEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        reg: ModbusSelectDef,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._reg = reg
        self._attr_unique_id = f"{entry.entry_id}_{reg.key}"
        self._attr_name = reg.name
        self._attr_translation_key = reg.key
        self._attr_options = reg.options
        self._attr_icon = reg.icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._current_option: str | None = reg.options[0] if reg.options else None

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if state and state.state in self._reg.options:
            self._current_option = state.state
        # Seed the coordinator cache so switch.py can read dispatch_mode immediately.
        if self._current_option:
            self._coordinator.selects[self._reg.key] = self._current_option
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        # For register-backed selects, prefer the live coordinator value so the
        # dropdown reflects the actual inverter state rather than the last HA state.
        if self._reg.sensor_key and self._coordinator.data:
            raw = self._coordinator.data.get(self._reg.sensor_key)
            if raw is not None:
                try:
                    idx = self._reg.values.index(int(raw))
                    return self._reg.options[idx]
                except (ValueError, IndexError):
                    pass
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        self._current_option = option
        self._coordinator.selects[self._reg.key] = option
        self.async_write_ha_state()

        if self._reg.key in LOCAL_ONLY_SELECTS:
            return

        idx = self._reg.options.index(option)
        value = self._reg.values[idx]
        await self._coordinator.async_write_register(self._reg.address, value)

        if self._reg.key == "dispatch_mode":
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            sw = switches.get("dispatch")
            if sw and sw.is_on:
                await sw.async_turn_on()
