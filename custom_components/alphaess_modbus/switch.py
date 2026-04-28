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

from .const import DOMAIN, DISPATCH_MODE_SOC_CONTROL, DISPATCH_SOC_SCALE, SOC_CALIBRATION_ADDR
from .coordinator import AlphaESSCoordinator

_LOGGER = logging.getLogger(__name__)


def _calc_pv_production(data: dict) -> int | None:
    keys = ["pv1_power", "pv2_power", "pv3_power", "pv4_power", "active_power_pv_meter"]
    if any(data.get(k) is None for k in keys):
        return None
    return max(0, sum(int(data[k]) for k in keys))


def _calc_house_load(data: dict) -> int | None:
    grid = data.get("power_grid")
    if grid is None:
        return None
    if float(data.get("inverter_work_mode", 0)) == 2:
        return round(float(grid))
    pv = _calc_pv_production(data)
    battery = data.get("power_battery")
    if pv is None or battery is None:
        return None
    return max(0, int(pv) + int(battery) + int(grid))

# Switches that are mutually exclusive — turning one on turns all others off.
_MUTEX_SWITCHES = [
    "force_charging",
    "force_discharging",
    "force_export",
    "force_import",
    "dispatch",
    "excess_export",
    "smart_export",
]

SWITCH_DEFS = [
    {"key": "force_charging",      "name": "Force Charging",       "icon": "mdi:battery-charging"},
    {"key": "force_discharging",   "name": "Force Discharging",    "icon": "mdi:battery-arrow-down"},
    {"key": "force_export",        "name": "Force Export",         "icon": "mdi:transmission-tower-export"},
    {"key": "force_import",        "name": "Force Import",         "icon": "mdi:transmission-tower-import"},
    {"key": "force_import_pause",  "name": "Force Import Pause",   "icon": "mdi:pause-circle"},
    {"key": "dispatch",            "name": "Dispatch",             "icon": "mdi:button-pointer"},
    {"key": "excess_export",       "name": "Excess Export",        "icon": "mdi:solar-power"},
    {"key": "excess_export_pause", "name": "Excess Export Pause",  "icon": "mdi:pause-circle"},
    {"key": "smart_export",        "name": "Smart Export",         "icon": "mdi:transmission-tower-export"},
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [AlphaESSSwitch(coordinator, entry, d) for d in SWITCH_DEFS]

    # Store references so switches can interact with each other
    hass.data[DOMAIN][f"{entry.entry_id}_switches"] = {e.switch_key: e for e in entities}

    calibration_switch = AlphaESSCalibrationSwitch(coordinator, entry)
    async_add_entities(entities + [calibration_switch])


def _get_number(hass: HomeAssistant, entry_id: str, key: str, default: float) -> float:
    entity_id = f"number.alphaess_inverter_{key}"
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
        self._attr_translation_key = self.switch_key
        self._attr_icon = definition["icon"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._is_on = False
        self._timer_cancel: asyncio.TimerHandle | None = None
        self._duration_cancel: asyncio.TimerHandle | None = None
        self._soc_unsub: Any | None = None

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if state and state.state == "on":
            self._is_on = False  # Don't auto-resume dispatch on restart

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.switch_key in ("excess_export_pause", "force_import_pause"):
            await self._handle_pause_turn_on()
            return

        # Mutual exclusion: turn off all other mutex switches first
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        for key, sw in switches.items():
            if key in _MUTEX_SWITCHES and key != self.switch_key and sw.is_on:
                await sw._async_turn_off_silent()

        self._is_on = True
        self.async_write_ha_state()

        try:
            if self.switch_key == "force_charging":
                await self._start_force_charging()
            elif self.switch_key == "force_discharging":
                duration_min = self._num("force_discharging_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force discharging duration is 0 — set number.alphaess_inverter_force_discharging_duration to a non-zero value")
                await self._start_force_discharging()
                self._schedule_duration_off(duration_s)
                self._start_soc_watcher("below", "force_discharging_cutoff_soc", 10.0)
            elif self.switch_key == "force_export":
                duration_min = self._num("force_export_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force export duration is 0 — set number.alphaess_inverter_force_export_duration to a non-zero value")
                await self._start_force_export()
                self._schedule_duration_off(duration_s)
                self._start_soc_watcher("below", "force_export_cutoff_soc", 4.0)
            elif self.switch_key == "force_import":
                duration_min = self._num("force_import_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force import duration is 0 — set number.alphaess_inverter_force_import_duration to a non-zero value")
                await self._start_force_import()
                self._schedule_duration_off(duration_s)
            elif self.switch_key == "dispatch":
                await self._start_dispatch()
            elif self.switch_key == "excess_export":
                await self._start_excess_export()
            elif self.switch_key == "smart_export":
                await self._start_smart_export()
        except Exception as err:
            _LOGGER.error("Failed to start %s: %s", self.switch_key, err)
            self._is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.switch_key in ("excess_export_pause", "force_import_pause"):
            await self._handle_pause_turn_off()
            return
        await self._async_turn_off_silent()

    async def _async_turn_off_silent(self) -> None:
        self._is_on = False
        self._cancel_timer()
        self.async_write_ha_state()
        await self._coordinator.async_reset_dispatch()
        # When a switch with a paired pause stops, also clear the pause switch
        pause_key = None
        if self.switch_key == "excess_export":
            pause_key = "excess_export_pause"
        elif self.switch_key == "force_import":
            pause_key = "force_import_pause"
        if pause_key:
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            pause_sw = switches.get(pause_key)
            if pause_sw and pause_sw.is_on:
                pause_sw._is_on = False
                pause_sw._cancel_timer()
                pause_sw.async_write_ha_state()

    def _cancel_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel.cancel()
            self._timer_cancel = None
        if self._duration_cancel:
            self._duration_cancel.cancel()
            self._duration_cancel = None
        if self._soc_unsub:
            self._soc_unsub()
            self._soc_unsub = None

    def _cancel_refresh_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel.cancel()
            self._timer_cancel = None

    def _schedule_duration_off(self, duration_seconds: int) -> None:
        if self._duration_cancel:
            self._duration_cancel.cancel()
        loop = self.hass.loop

        async def _turn_off():
            await self._async_turn_off_silent()

        def _callback():
            asyncio.ensure_future(_turn_off(), loop=loop)

        self._duration_cancel = loop.call_later(duration_seconds, _callback)

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

    def _get_dispatch_mode(self) -> int:
        """Read the dispatch mode value from the select entity option string e.g. 'Load Following (3)'."""
        entity_id = "select.alphaess_inverter_dispatch_mode"
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return int(state.state.split("(")[-1].split(")")[0])
            except (ValueError, IndexError):
                pass
        return DISPATCH_MODE_SOC_CONTROL

    def _start_soc_watcher(self, direction: str, param_key: str, default: float) -> None:
        """Watch soc_battery via coordinator and stop this switch when the cutoff is reached.

        Fires on every coordinator update where soc_battery is present (~10 s cadence).
        Reads the cutoff number entity dynamically so mid-session changes take effect.
        direction='below': stop when soc <= cutoff  (discharge/export)
        direction='above': stop when soc >= cutoff  (charge)
        """
        if self._soc_unsub:
            self._soc_unsub()
            self._soc_unsub = None

        def _check() -> None:
            if not self._is_on:
                return
            data = self._coordinator.data or {}
            soc = data.get("soc_battery")
            if soc is None:
                return
            soc = float(soc)
            cutoff = self._num(param_key, default)
            # Stop 1% before the inverter's own internal limit so the dispatch
            # is still active (battery still meets house load) while the reset
            # is sent - this guarantees no grid draw during the transition.
            triggered = (
                (direction == "below" and soc <= cutoff + 1.0)
                or (direction == "above" and soc >= cutoff - 1.0)
            )
            if not triggered:
                return
            unsub = self._soc_unsub
            self._soc_unsub = None
            if unsub:
                unsub()
            asyncio.ensure_future(self._async_turn_off_silent(), loop=self.hass.loop)

        self._soc_unsub = self._coordinator.async_add_listener(_check)

    # ------------------------------------------------------------------
    # Force Charging
    # ------------------------------------------------------------------

    async def _start_force_charging(self) -> None:
        power_kw = self._num("force_charging_power", 5.0)
        cutoff_soc = self._num("force_charging_cutoff_soc", 100.0)
        duration_min = self._num("force_charging_duration", 120.0)
        duration_s = int(duration_min * 60)
        if duration_s <= 0:
            raise ValueError("Force charging duration is 0 — set number.alphaess_inverter_force_charging_duration to a non-zero value")
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 - power_kw * 1000)

        await self._coordinator.async_write_dispatch([
            1,
            0, power_raw,
            0, 32000,
            DISPATCH_MODE_SOC_CONTROL,
            soc_raw,
            0, duration_s,
        ])
        self._schedule_auto_off(duration_s)

    # ------------------------------------------------------------------
    # Force Discharging
    # ------------------------------------------------------------------

    async def _start_force_discharging(self) -> None:
        data = self._coordinator.data or {}
        soc = data.get("soc_battery")
        power_kw = self._num("force_discharging_power", 5.0)
        cutoff_soc = self._num("force_discharging_cutoff_soc", 10.0)
        if soc is not None and float(soc) <= cutoff_soc:
            await self._async_turn_off_silent()
            return
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + power_kw * 1000)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 60,
        ])
        self._schedule_force_discharging_refresh()

    def _schedule_force_discharging_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            await self._start_force_discharging()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(50, _callback)

    # ------------------------------------------------------------------
    # Force Export
    # ------------------------------------------------------------------

    async def _start_force_export(self) -> None:
        data = self._coordinator.data or {}
        soc = data.get("soc_battery")
        power_kw = self._num("force_export_power", 5.0)
        cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
        if soc is not None and float(soc) <= cutoff_soc:
            await self._async_turn_off_silent()
            return
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + power_kw * 1000)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 60,
        ])
        self._schedule_force_export_refresh()

    def _schedule_force_export_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            await self._start_force_export()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(50, _callback)

    # ------------------------------------------------------------------
    # Generic Dispatch
    # ------------------------------------------------------------------

    async def _start_dispatch(self) -> None:
        power_kw = self._num("dispatch_power", 0.0)
        cutoff_soc = self._num("dispatch_cutoff_soc", 100.0)
        duration_min = self._num("dispatch_duration", 120.0)
        duration_s = int(duration_min * 60)
        mode_val = self._get_dispatch_mode()

        # Modes 1/2/3/5 use the power offset; modes 4/6/7/19 use neutral (32000)
        if mode_val in (1, 2, 3, 5):
            power_raw = int(32000 + power_kw * 1000)
        else:
            power_raw = 32000

        # SoC target only applies in mode 2 (State of Charge Control)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE) if mode_val == DISPATCH_MODE_SOC_CONTROL else 0

        await self._coordinator.async_write_dispatch([
            1,
            0, power_raw,
            0, 32000,
            mode_val,
            soc_raw,
            0, duration_s,
        ])
        self._schedule_auto_off(duration_s)

    # ------------------------------------------------------------------
    # Excess Export
    # ------------------------------------------------------------------

    async def _start_excess_export(self) -> None:
        await self._coordinator.async_write_dispatch([
            1,
            0, 32000,
            0, 32000,
            DISPATCH_MODE_SOC_CONTROL,
            255,
            0, 300,
        ])
        self._schedule_excess_export_refresh()

    def _schedule_excess_export_refresh(self) -> None:
        self._cancel_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            pause_sw = switches.get("excess_export_pause")
            if pause_sw and pause_sw.is_on:
                # Paused — reschedule without re-dispatching
                self._schedule_excess_export_refresh()
                return
            await self._start_excess_export()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(240, _callback)

    # ------------------------------------------------------------------
    # Excess Export Pause
    # ------------------------------------------------------------------

    async def _handle_pause_turn_on(self) -> None:
        self._is_on = True
        self.async_write_ha_state()
        try:
            # Write stopped-state dispatch; same payload as reset (start=0, 90s window)
            await self._coordinator.async_reset_dispatch()
        except Exception as err:
            _LOGGER.error("Failed to start excess_export_pause: %s", err)
            self._is_on = False
            self.async_write_ha_state()

    async def _handle_pause_turn_off(self) -> None:
        self._is_on = False
        self._cancel_timer()
        self.async_write_ha_state()
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        if self.switch_key == "excess_export_pause":
            parent_sw = switches.get("excess_export")
            if parent_sw and parent_sw.is_on:
                try:
                    await parent_sw._start_excess_export()
                except Exception as err:
                    _LOGGER.error("Failed to resume excess_export after pause: %s", err)
        elif self.switch_key == "force_import_pause":
            parent_sw = switches.get("force_import")
            if parent_sw and parent_sw.is_on:
                try:
                    await parent_sw._start_force_import()
                except Exception as err:
                    _LOGGER.error("Failed to resume force_import after pause: %s", err)

    # ------------------------------------------------------------------
    # Force Import
    # ------------------------------------------------------------------

    async def _start_force_import(self) -> None:
        d = self._coordinator.data or {}
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            self._schedule_force_import_refresh()
            return
        import_power_kw = self._num("force_import_power", 5.0)
        cutoff_soc = self._num("force_import_cutoff_soc", 100.0)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        charge_power_w = max(0, int(import_power_kw * 1000) - int(house_load_w) + int(pv_production_w))
        power_raw = int(32000 - charge_power_w)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 30,
        ])
        self._schedule_force_import_refresh()

    def _schedule_force_import_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            pause_sw = switches.get("force_import_pause")
            if pause_sw and pause_sw.is_on:
                self._schedule_force_import_refresh()
                return
            await self._start_force_import()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(25, _callback)

    # ------------------------------------------------------------------
    # Smart Export
    # ------------------------------------------------------------------

    async def _start_smart_export(self) -> None:
        d = self._coordinator.data or {}
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            self._schedule_smart_refresh("smart_export")
            return
        max_export_kw = self._num("max_export_power", 5.0)
        cutoff_soc = self._num("force_export_cutoff_soc", 10.0)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        charge_power_w = max(0, int(max_export_kw * 1000) + int(house_load_w) - int(pv_production_w))
        power_raw = int(32000 + charge_power_w)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 30,
        ])
        self._schedule_smart_refresh()

    # ------------------------------------------------------------------
    # 30s refresh for smart_export
    # ------------------------------------------------------------------

    def _schedule_smart_refresh(self) -> None:
        self._cancel_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            await self._start_smart_export()

        def _callback():
            asyncio.ensure_future(_refresh(), loop=loop)

        self._timer_cancel = loop.call_later(30, _callback)


class AlphaESSCalibrationSwitch(SwitchEntity):
    """Switch that reflects and controls the inverter's SOC calibration cycle (0x1901).

    State is read back from the inverter every 60 s via the soc_calibration sensor
    so HA accurately shows when the cycle finishes and the inverter self-clears the flag.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_soc_calibration"
        self._attr_name = "SOC Calibration"
        self._attr_translation_key = "soc_calibration"
        self._attr_icon = "mdi:battery-sync"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._unsub: Any = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._coordinator.data is not None

    @property
    def is_on(self) -> bool:
        if not self._coordinator.data:
            return False
        return int(self._coordinator.data.get("soc_calibration", 0)) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._coordinator.async_write_register(SOC_CALIBRATION_ADDR, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coordinator.async_write_register(SOC_CALIBRATION_ADDR, 0)
