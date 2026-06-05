from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, NUMBER_REGISTERS, ModbusNumberDef
from .coordinator import AlphaESSCoordinator

# These numbers feed into dispatch sequences rather than a single register write.
# The switch entities read these values when starting a dispatch operation.
DISPATCH_PARAM_KEYS = {
    "force_charging_cutoff_soc",
    "force_charging_duration",
    "force_charging_power",
    "force_discharging_cutoff_soc",
    "force_discharging_duration",
    "force_discharging_power",
    "force_export_cutoff_soc",
    "force_export_duration",
    "force_export_power",
    "force_import_cutoff_soc",
    "force_import_duration",
    "force_import_power",
    "dispatch_cutoff_soc",
    "dispatch_duration",
    "dispatch_power",
}

# Maps param key prefix (or exact key) to the switch that owns it
_PARAM_SWITCH = {
    "force_charging": "force_charging",
    "force_discharging": "force_discharging",
    "force_export": "force_export",
    "force_import": "force_import",
    "dispatch": "dispatch",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AlphaESSNumber(coordinator, entry, reg)
        for reg in NUMBER_REGISTERS
    )


class AlphaESSNumber(RestoreEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        reg: ModbusNumberDef,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._reg = reg
        self._attr_unique_id = f"{entry.entry_id}_{reg.key}"
        self._attr_name = reg.name
        self._attr_translation_key = reg.key
        self._attr_native_step = reg.step
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = reg.icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._value: float = reg.default_value if reg.default_value is not None else reg.min_value

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if state and state.state not in ("unknown", "unavailable"):
            try:
                self._value = float(state.state)
            except ValueError:
                pass
        # Seed the coordinator cache so switch.py can read it immediately.
        self._coordinator.numbers[self._reg.key] = self._value
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def native_max_value(self) -> float:
        if self._reg.ac_limit_scaled:
            return self._coordinator.ac_limit_w / 1000
        return self._reg.max_value

    @property
    def native_min_value(self) -> float:
        if self._reg.ac_limit_scaled and self._reg.min_value < 0:
            return -(self._coordinator.ac_limit_w / 1000)
        return self._reg.min_value

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        # For register-backed numbers, prefer the live coordinator value so the
        # slider reflects what the inverter actually has rather than the last
        # HA-saved state (which may have drifted if the inverter was changed via
        # the app or another client).
        if self._reg.address is not None and self._coordinator.data:
            v = self._coordinator.data.get(self._reg.key)
            if v is not None:
                return float(v)
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        self._coordinator.numbers[self._reg.key] = value
        # Optimistically mirror the new value into coordinator.data so native_value
        # returns the written value immediately instead of the stale polled value.
        if self._reg.address is not None and self._coordinator.data is not None:
            self._coordinator.data[self._reg.key] = value
        self.async_write_ha_state()

        if self._reg.key in DISPATCH_PARAM_KEYS:
            await self._refire_if_active()
            return

        if self._reg.address is None:
            return

        # Direct single-register write
        await self._coordinator.async_write_register(self._reg.address, int(value))

    async def _refire_if_active(self) -> None:
        switch_key = next(
            (sw for prefix, sw in _PARAM_SWITCH.items() if self._reg.key.startswith(prefix)),
            None,
        )
        if not switch_key:
            return
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        sw = switches.get(switch_key)
        if sw and sw.is_on:
            await sw.async_turn_on()
