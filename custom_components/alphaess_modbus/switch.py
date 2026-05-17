from __future__ import annotations

import asyncio
import logging
import time
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
]

SWITCH_DEFS = [
    {"key": "force_charging",      "name": "Force Charging",       "icon": "mdi:battery-charging"},
    {"key": "force_charging_hold", "name": "Force Charging Hold",  "icon": "mdi:battery-lock"},
    {"key": "force_discharging",   "name": "Force Discharging",    "icon": "mdi:battery-arrow-down"},
    {"key": "force_export",        "name": "Force Export",         "icon": "mdi:transmission-tower-export"},
    {"key": "force_export_hold",   "name": "Force Export Hold",    "icon": "mdi:transmission-tower-export"},
    {"key": "force_import",        "name": "Force Import",         "icon": "mdi:transmission-tower-import"},
    {"key": "force_import_hold",   "name": "Force Import Hold",    "icon": "mdi:battery-lock"},
    {"key": "dispatch",            "name": "Dispatch",             "icon": "mdi:button-pointer"},
    {"key": "excess_export",       "name": "Excess Export",        "icon": "mdi:solar-power"},
]

_HOLD_SWITCHES = {"force_charging_hold", "force_export_hold", "force_import_hold"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [AlphaESSSwitch(coordinator, entry, d) for d in SWITCH_DEFS]

    # Store references so switches can interact with each other
    hass.data[DOMAIN][f"{entry.entry_id}_switches"] = {e.switch_key: e for e in entities}

    async_add_entities(entities)




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
        self._pending_tasks: set[asyncio.Task] = set()
        # Excess export auto-pause watcher state
        self._ee_listener_unsub: Any | None = None
        self._ee_last_pause_time: float = 0.0
        self._ee_last_resume_time: float = 0.0
        self._ee_work_mode_1_since: float | None = None
        self._ee_above_limit: bool | None = None

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if state and state.state == "on":
            self._is_on = False  # Don't auto-resume dispatch on restart
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_timer()
        for task in list(self._pending_tasks):
            task.cancel()
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.switch_key in _HOLD_SWITCHES:
            self._is_on = True
            self.async_write_ha_state()
            return

        # Mutual exclusion: turn off all other mutex switches first
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        for key, sw in switches.items():
            if key in _MUTEX_SWITCHES and key != self.switch_key and sw.is_on:
                await sw._async_turn_off_silent()

        self._is_on = True
        self._coordinator.active_dispatch_key = self.switch_key
        self.async_write_ha_state()

        try:
            if self.switch_key == "force_charging":
                await self._start_force_charging()
            elif self.switch_key == "force_discharging":
                duration_min = self._num("force_discharging_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force discharging duration is 0 — set number.alphaess_inverter_force_discharging_duration to a non-zero value")
                await self._start_force_discharging(duration_s)
                self._schedule_duration_off(duration_s)
                self._start_soc_watcher("below", "force_discharging_cutoff_soc", 10.0)
            elif self.switch_key == "force_export":
                duration_min = self._num("force_export_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force export duration is 0 — set number.alphaess_inverter_force_export_duration to a non-zero value")
                await self._start_force_export(duration_s)
                self._schedule_duration_off(duration_s)
                self._start_soc_watcher("below", "force_export_cutoff_soc", 4.0)
            elif self.switch_key == "force_import":
                duration_min = self._num("force_import_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force import duration is 0 — set number.alphaess_inverter_force_import_duration to a non-zero value")
                await self._start_force_import(duration_s)
                self._schedule_duration_off(duration_s)
            elif self.switch_key == "dispatch":
                await self._start_dispatch()
            elif self.switch_key == "excess_export":
                await self._start_excess_export()
        except Exception as err:
            _LOGGER.error("Failed to start %s: %s", self.switch_key, err)
            self._is_on = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.switch_key in _HOLD_SWITCHES:
            self._is_on = False
            self.async_write_ha_state()
            return
        await self._async_turn_off_silent()

    async def _async_turn_off_silent(self) -> None:
        self._is_on = False
        if self._coordinator.active_dispatch_key == self.switch_key:
            self._coordinator.active_dispatch_key = None
        self._cancel_timer()
        self.async_write_ha_state()
        if self.switch_key in _HOLD_SWITCHES:
            return
        await self._coordinator.async_reset_dispatch()
        if self.switch_key == "excess_export":
            self._coordinator.ee_paused = False
        elif self.switch_key == "force_import":
            if self._coordinator.fi_paused:
                self._coordinator.fi_paused = False

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
        if self._ee_listener_unsub:
            self._ee_listener_unsub()
            self._ee_listener_unsub = None
        self._ee_above_limit = None

    def _cancel_refresh_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel.cancel()
            self._timer_cancel = None

    def _schedule_duration_off(self, duration_seconds: int) -> None:
        if self._duration_cancel:
            self._duration_cancel.cancel()
        loop = self.hass.loop

        async def _turn_off():
            hold_key = None
            if self.switch_key == "force_charging":
                hold_key = "force_charging_hold"
            elif self.switch_key == "force_export":
                hold_key = "force_export_hold"
            elif self.switch_key == "force_import":
                hold_key = "force_import_hold"
            if hold_key:
                switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
                hold_sw = switches.get(hold_key)
                if hold_sw and hold_sw.is_on:
                    if self.switch_key == "force_charging":
                        await self._start_force_charging_hold()
                    elif self.switch_key == "force_export":
                        await self._start_force_export_hold()
                    # force_import: refresh loop is already running — just don't stop
                    return
            await self._async_turn_off_silent()

        def _callback():
            task = self.hass.async_create_task(_turn_off(), name=f"alphaess_{self.switch_key}_duration_off")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._duration_cancel = loop.call_later(duration_seconds, _callback)

    def _schedule_auto_off(self, duration_seconds: int) -> None:
        self._cancel_timer()
        loop = self.hass.loop

        async def _turn_off():
            await self._async_turn_off_silent()

        def _callback():
            task = self.hass.async_create_task(_turn_off(), name=f"alphaess_{self.switch_key}_auto_off")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(duration_seconds, _callback)

    def _num(self, key: str, default: float) -> float:
        v = self._coordinator.get_number(key)
        return v if v is not None else default

    def _get_dispatch_mode(self) -> int:
        """Read the dispatch mode int from the coordinator select cache."""
        option = self._coordinator.get_select("dispatch_mode")
        if option:
            try:
                return int(option.split("(")[-1].split(")")[0])
            except (ValueError, IndexError):
                pass
        return DISPATCH_MODE_SOC_CONTROL

    async def async_force_off(self) -> None:
        """Unconditionally mark this switch off and cancel its timers.

        Used by other switches/buttons that need to clear state without
        triggering a full dispatch reset (which is the caller's responsibility).
        """
        self._is_on = False
        if self._coordinator.active_dispatch_key == self.switch_key:
            self._coordinator.active_dispatch_key = None
        self._cancel_timer()
        self.async_write_ha_state()

    async def async_force_on(self) -> None:
        """Unconditionally mark this switch on without starting any dispatch."""
        self._is_on = True
        self.async_write_ha_state()

    def _start_soc_watcher(self, direction: str, param_key: str, default: float) -> None:
        """Watch soc_battery via coordinator and stop this switch when the cutoff is reached.

        Activates fast SOC sampling (2 s) while the watcher is alive.
        direction='below': stop when soc <= cutoff  (discharge/export)
        direction='above': stop when soc >= cutoff  (charge)
        """
        if self._soc_unsub:
            # Already watching — unsubscribe first (decrements fast-SOC refcount).
            self._soc_unsub()
            self._soc_unsub = None

        self._coordinator.set_fast_soc(True)

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
                unsub()  # decrements fast-SOC refcount via _combined_unsub
            task = self.hass.async_create_task(self._async_turn_off_silent(), name=f"alphaess_{self.switch_key}_soc_off")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        raw_unsub = self._coordinator.async_add_listener(_check)

        def _combined_unsub() -> None:
            raw_unsub()
            self._coordinator.set_fast_soc(False)

        self._soc_unsub = _combined_unsub

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

    async def _start_force_charging_hold(self) -> None:
        """Neutral hold dispatch — keeps inverter in dispatch mode to prevent discharge."""
        cutoff_soc = self._num("force_charging_cutoff_soc", 100.0)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        await self._coordinator.async_write_dispatch([
            1, 0, 32000, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 60,
        ])
        self._schedule_force_charging_hold_refresh()

    def _schedule_force_charging_hold_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            hold_sw = switches.get("force_charging_hold")
            if hold_sw and hold_sw.is_on:
                await self._start_force_charging_hold()
            else:
                await self._async_turn_off_silent()

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_hold_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(50, _callback)

    # ------------------------------------------------------------------
    # Force Discharging
    # ------------------------------------------------------------------

    async def _start_force_discharging(self, duration_s: int) -> None:
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
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, duration_s,
        ])
        self._schedule_force_discharging_refresh()

    def _schedule_force_discharging_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            await self._start_force_discharging(int(self._num("force_discharging_duration", 120.0) * 60))

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_discharge_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(50, _callback)

    # ------------------------------------------------------------------
    # Force Export
    # ------------------------------------------------------------------

    async def _start_force_export(self, duration_s: int) -> None:
        d = self._coordinator.data or {}
        soc = d.get("soc_battery")
        cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
        if soc is not None and float(soc) <= cutoff_soc:
            await self._async_turn_off_silent()
            return
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            self._schedule_force_export_refresh()
            return
        target_export_w = int(self._num("force_export_power", 5.0) * 1000)
        battery_discharge_w = max(0, target_export_w + int(house_load_w) - int(pv_production_w))
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + battery_discharge_w)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, duration_s,
        ])
        self._schedule_force_export_refresh()

    def _schedule_force_export_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            await self._start_force_export(int(self._num("force_export_duration", 120.0) * 60))

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_export_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(25, _callback)

    async def _start_force_export_hold(self) -> None:
        """Restart Force Export dispatch for a fresh 60 s window to keep it running indefinitely."""
        d = self._coordinator.data or {}
        soc = d.get("soc_battery")
        cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
        if soc is not None and float(soc) <= cutoff_soc:
            await self._async_turn_off_silent()
            return
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            self._schedule_force_export_hold_refresh()
            return
        target_export_w = int(self._num("force_export_power", 5.0) * 1000)
        battery_discharge_w = max(0, target_export_w + int(house_load_w) - int(pv_production_w))
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        power_raw = int(32000 + battery_discharge_w)
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, 60,
        ])
        self._schedule_force_export_hold_refresh()

    def _schedule_force_export_hold_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
            hold_sw = switches.get("force_export_hold")
            if hold_sw and hold_sw.is_on:
                await self._start_force_export_hold()
            else:
                await self._async_turn_off_silent()

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_hold_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

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
        if not self._is_on:
            return
        d = self._coordinator.data or {}
        pv_total = _calc_pv_production(d)
        if pv_total is not None:
            pv_dc = pv_total - int(d.get("active_power_pv_meter", 0))
            if pv_dc > self._coordinator.ac_limit_w:
                power_raw = max(0, 32000 - (pv_dc - self._coordinator.ac_limit_w))
            else:
                power_raw = 32000
        else:
            power_raw = 32000
        await self._coordinator.async_write_dispatch([
            1, 0, power_raw, 0, 32000,
            DISPATCH_MODE_SOC_CONTROL, 255, 0, 300,
        ])
        self._schedule_excess_export_refresh()
        self._start_ee_watcher()

    def _schedule_excess_export_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            if self._coordinator.ee_paused:
                self._schedule_excess_export_refresh()
                return
            await self._start_excess_export()

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_ee_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(240, _callback)

    def _start_ee_watcher(self) -> None:
        """Subscribe to coordinator updates to auto-pause/resume Excess Export.

        Mirrors upstream AlphaESS_Excess_Export_Pause / _Resume automations:
        - Pause when power_grid > 50 W (importing) or inverter not in normal mode.
        - Resume when PV > 100 W, excess > 50 W or grid < -500 W, inverter in
          normal mode for >= 10 min, and >= 15 s since last pause.
        Both transitions include a 15-second debounce to prevent flapping.
        """
        if self._ee_listener_unsub is not None:
            return

        # If work mode is already normal, credit the 10-minute guard immediately
        # so a user who just turned on EE doesn't wait 10 min for the first resume.
        d = self._coordinator.data or {}
        wm = d.get("inverter_work_mode")
        if wm is not None and int(float(wm)) == 1:
            self._ee_work_mode_1_since = time.monotonic() - 600
        else:
            self._ee_work_mode_1_since = None

        pv_total_init = _calc_pv_production(d)
        if pv_total_init is not None:
            pv_dc_init = pv_total_init - int(d.get("active_power_pv_meter", 0))
            self._ee_above_limit = pv_dc_init > self._coordinator.ac_limit_w

        def _check() -> None:
            if not self._is_on:
                return
            d = self._coordinator.data or {}
            grid = d.get("power_grid")
            if grid is None:
                return
            wm = d.get("inverter_work_mode")
            work_mode_normal = wm is not None and int(float(wm)) == 1
            now = time.monotonic()

            if work_mode_normal:
                if self._ee_work_mode_1_since is None:
                    self._ee_work_mode_1_since = now
            else:
                self._ee_work_mode_1_since = None

            if not self._coordinator.ee_paused:
                should_pause_grid = float(grid) > 50 and (now - self._ee_last_resume_time) >= 15
                should_pause_mode = not work_mode_normal
                if should_pause_grid or should_pause_mode:
                    self._coordinator.ee_paused = True
                    self._ee_last_pause_time = now
                    self._ee_above_limit = None
                    task = self.hass.async_create_task(
                        self._coordinator.async_reset_dispatch(),
                        name="alphaess_ee_auto_pause",
                    )
                    self._pending_tasks.add(task)
                    task.add_done_callback(self._pending_tasks.discard)
                else:
                    pv_total = _calc_pv_production(d)
                    if pv_total is not None:
                        pv_dc = pv_total - int(d.get("active_power_pv_meter", 0))
                        above = pv_dc > self._coordinator.ac_limit_w
                        if above != self._ee_above_limit:
                            self._ee_above_limit = above
                            task = self.hass.async_create_task(
                                self._start_excess_export(),
                                name="alphaess_ee_regime_change",
                            )
                            self._pending_tasks.add(task)
                            task.add_done_callback(self._pending_tasks.discard)
            else:
                pv_total = _calc_pv_production(d)
                pv = pv_total or 0
                hl = _calc_house_load(d) or 0
                excess = max(0, pv - hl)
                work_mode_ok = (
                    work_mode_normal
                    and self._ee_work_mode_1_since is not None
                    and (now - self._ee_work_mode_1_since) >= 600
                )
                if (
                    work_mode_ok
                    and (now - self._ee_last_pause_time) >= 15
                    and pv > 100
                    and (excess > 50 or float(grid) < -500)
                ):
                    self._coordinator.ee_paused = False
                    self._ee_last_resume_time = now
                    if pv_total is not None:
                        pv_dc = pv_total - int(d.get("active_power_pv_meter", 0))
                        self._ee_above_limit = pv_dc > self._coordinator.ac_limit_w
                    else:
                        self._ee_above_limit = None
                    task = self.hass.async_create_task(
                        self._start_excess_export(),
                        name="alphaess_ee_auto_resume",
                    )
                    self._pending_tasks.add(task)
                    task.add_done_callback(self._pending_tasks.discard)

        self._ee_listener_unsub = self._coordinator.async_add_listener(_check)

    # ------------------------------------------------------------------
    # Force Import
    # ------------------------------------------------------------------

    async def _start_force_import(self, duration_s: int) -> None:
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
            1, 0, power_raw, 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, duration_s,
        ])
        self._schedule_force_import_refresh()

    def _schedule_force_import_refresh(self) -> None:
        self._cancel_refresh_timer()
        loop = self.hass.loop

        async def _refresh():
            if not self._is_on:
                return
            if self._coordinator.fi_paused:
                self._schedule_force_import_refresh()
                return
            await self._start_force_import(int(self._num("force_import_duration", 120.0) * 60))

        def _callback():
            task = self.hass.async_create_task(_refresh(), name=f"alphaess_{self.switch_key}_import_refresh")
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)

        self._timer_cancel = loop.call_later(25, _callback)

