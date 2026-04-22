from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DISPATCH_MODE_SOC_CONTROL, DISPATCH_SOC_SCALE
from .coordinator import AlphaESSCoordinator

_LOGGER = logging.getLogger(__name__)

# Only one dispatch mode can be active at a time.
_MUTEX_SWITCHES = [
    "force_charging",
    "force_discharging",
    "force_export",
    "excess_export",
]

SWITCH_DEFS = [
    {"key": "force_charging",    "name": "Force Charging",    "icon": "mdi:battery-charging"},
    {"key": "force_discharging", "name": "Force Discharging", "icon": "mdi:battery-arrow-down"},
    {"key": "force_export",      "name": "Force Export",      "icon": "mdi:transmission-tower-export"},
    {"key": "excess_export",     "name": "Excess Export",     "icon": "mdi:solar-power"},
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [AlphaESSSwitch(coordinator, entry, d) for d in SWITCH_DEFS]

    # Store references so switches can turn each other off
    hass.data[DOMAIN][f"{entry.entry_id}_switches"] = {e.switch_key: e for e in entities}
    async_add_entities(entities)


def _get_number(hass: HomeAssistant, entry_id: str, key: str, default: float) -> float:
    entity_id = f"number.alphaess_{key}"
    state = hass.states.get(entity_id)
    if state and state.state not in ("unknown", "unavailable"):
        try:
            return float(state.state)
        except ValueError:
            pass
    return default


class AlphaESSSwitch(RestoreEntity, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        definition: dict,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self.switch_key = definition["key"]
        self._attr_unique_id = f"{entry.entry_id}_{self.switch_key}"
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._is_on = False
        self._timer_cancel: asyncio.TimerHandle | None = None

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if state and state.state == "on":
            self._is_on = False  # Don't auto-resume dispatch on restart

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn off all other mutex switches first
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        for key, sw in switches.items():
            if key != self.switch_key and sw.is_on:
                await sw._async_turn_off_silent()

        self._is_on = True
        self.async_write_ha_state()

        try:
            if self.switch_key == "force_charging":
                await self._start_force_charging()
            elif self.switch_key == "force_discharging":
                await self._start_force_discharging()
            elif self.switch_key == "force_export":
                await self._start_force_export()
            elif self.switch_key == "excess_export":
                await self._start_excess_export()
        except Exception as err:
            _LOGGER.error("Failed to start %s: %s", self.switch_key, err)
            self._is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_turn_off_silent()

    async def _async_turn_off_silent(self) -> None:
        self._is_on = False
        self._cancel_timer()
        self.async_write_ha_state()
        await self._coordinator.async_reset_dispatch()

    def _cancel_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel.cancel()
            self._timer_cancel = None

    def _schedule_auto_off(self, duration_seconds: int) -> None:
        self._cancel_timer()
        loop = self.hass.loop

        async def _turn_off():
            await self._async_turn_off_silent()

        def _callback():
            asyncio.ensure_future(_turn_off(), loop=loop)

        self._timer_cancel = loop.call_later(duration_seconds, _callback)

    def _num(self, key: str, default: float) -> float:
        return _get_number(self.hass, self._entry.entry_id, key, default)

    async def _start_force_charging(self) -> None:
        power_kw = self._num("force_charging_power", 5.0)
        cutoff_soc = self._num("force_charging_cutoff_soc", 100.0)
        duration_min = self._num("force_charging_duration", 120.0)
        duration_s = int(duration_min * 60)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 - power_kw * 1000)

        await self._coordinator.async_write_dispatch([
            1,           # Dispatch Start
            0, power_raw,  # Active Power (hi word=0, lo=offset value)
            0, 32000,    # Reactive Power
            DISPATCH_MODE_SOC_CONTROL,
            soc_raw,
            0, duration_s,
        ])
        self._schedule_auto_off(duration_s)

    async def _start_force_discharging(self) -> None:
        power_kw = self._num("force_discharging_power", 5.0)
        cutoff_soc = self._num("force_discharging_cutoff_soc", 10.0)
        duration_min = self._num("force_discharging_duration", 120.0)
        duration_s = int(duration_min * 60)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + power_kw * 1000)

        await self._coordinator.async_write_dispatch([
            1,
            0, power_raw,
            0, 32000,
            DISPATCH_MODE_SOC_CONTROL,
            soc_raw,
            0, duration_s,
        ])
        self._schedule_auto_off(duration_s)

    async def _start_force_export(self) -> None:
        power_kw = self._num("force_export_power", 5.0)
        cutoff_soc = self._num("force_export_cutoff_soc", 100.0)
        duration_min = self._num("force_export_duration", 120.0)
        duration_s = int(duration_min * 60)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + power_kw * 1000)

        await self._coordinator.async_write_dispatch([
            1,
            0, power_raw,
            0, 32000,
            DISPATCH_MODE_SOC_CONTROL,
            soc_raw,
            0, duration_s,
        ])
        self._schedule_auto_off(duration_s)

    async def _start_excess_export(self) -> None:
        # Excess Export: dispatch battery to charge from PV excess,
        # inverter handles clipping. Uses a 5-minute dead-man's switch.
        # The coordinator will keep re-dispatching while the switch is on.
        await self._coordinator.async_write_dispatch([
            1,
            0, 32000,  # No forced power offset
            0, 32000,
            DISPATCH_MODE_SOC_CONTROL,
            255,       # Max SoC
            0, 300,    # 5-minute dead man's switch
        ])
        # Re-dispatch every 4 minutes to keep it alive
        self._schedule_excess_export_refresh()

    def _schedule_excess_export_refresh(self) -> None:
        self._cancel_timer()
        loop = self.hass.loop

        async def _refresh():
            if self._is_on:
                await self._start_excess_export()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(240, _callback)
