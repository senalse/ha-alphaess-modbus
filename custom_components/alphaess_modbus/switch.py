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

from .const import (
    DOMAIN,
    DISPATCH_MODE_SOC_CONTROL,
    DISPATCH_SOC_SCALE,
    DISPATCH_FLOW_DIRECTION,
    DISPATCH_PV_SWITCH_ADDR,
    DISPATCH_PV_ON,
    DISPATCH_PV_OFF,
    DISPATCH_PV_UNCHANGED,
)
from .coordinator import AlphaESSCoordinator

_LOGGER = logging.getLogger(__name__)

# Force Export / Force Import setpoint servo tuning.
# On every coordinator update (~2 s poll) the battery setpoint is trimmed so the
# measured grid power moves toward the target (export = -target, import = +target).
# This is a closed loop on the grid meter, NOT a feed-forward from the calculated
# house load: the house-load estimate is derived from battery + grid, so feeding it
# back drove a kilowatt-scale limit cycle (the battery's own output fed into its next
# command). Servoing on grid alone breaks that feedback.
#
# new_setpoint = last_setpoint + _SERVO_GAIN * grid_error
# With ~one poll of meter lag the loop is critically damped near gain 0.25, so a gain
# of 0.3 gives a fast, essentially overshoot-free response (important for zero-import
# export tariffs) and zero steady-state error. Raise for faster recovery, lower if it
# ever hunts. A rewrite is only issued once the setpoint moves by _SERVO_DEADBAND_W,
# with a _DISPATCH_STALE_REWRITE_S liveness fallback.
_SERVO_GAIN = 0.3
_SERVO_DEADBAND_W = 80
_DISPATCH_STALE_REWRITE_S = 60


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
    {"key": "force_discharging",      "name": "Force Discharging",      "icon": "mdi:battery-arrow-down"},
    {"key": "force_discharging_hold", "name": "Force Discharging Hold", "icon": "mdi:battery-lock"},
    {"key": "force_export",           "name": "Force Export",           "icon": "mdi:transmission-tower-export"},
    {"key": "force_export_hold",   "name": "Force Export Hold",    "icon": "mdi:transmission-tower-export"},
    {"key": "force_import",        "name": "Force Import",         "icon": "mdi:transmission-tower-import"},
    {"key": "force_import_hold",   "name": "Force Import Hold",    "icon": "mdi:battery-lock"},
    {"key": "dispatch",            "name": "Dispatch",             "icon": "mdi:button-pointer"},
    {"key": "excess_export",       "name": "Excess Export",        "icon": "mdi:solar-power"},
    {"key": "dispatch_pv",         "name": "Dispatch PV Enabled",  "icon": "mdi:solar-power"},
]

_HOLD_SWITCHES = {"force_charging_hold", "force_discharging_hold", "force_export_hold", "force_import_hold"}


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
        self._ee_last_power_raw: int | None = None
        self._ee_last_write_time: float = 0.0
        # Force Export event-driven watcher state
        self._fe_listener_unsub: Any | None = None
        self._fe_last_power_raw: int | None = None
        self._fe_last_write_time: float = 0.0
        # Force Import event-driven watcher state
        self._fi_listener_unsub: Any | None = None
        self._fi_last_power_raw: int | None = None
        self._fi_last_write_time: float = 0.0
        # Battery power watcher state
        self._bp_near_zero_since: float | None = None

    async def async_added_to_hass(self) -> None:
        state = await self.async_get_last_state()
        if self.switch_key == "dispatch_pv":
            # Persistent preference, not a dispatch. Default ON (PV enabled);
            # restore the last known state across restarts.
            self._is_on = True if state is None else state.state == "on"
        elif state and state.state == "on":
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
        if self.switch_key == "dispatch_pv":
            self._is_on = True
            self.async_write_ha_state()
            await self._maybe_write_pv_switch(DISPATCH_PV_ON)
            return

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
                self._start_battery_power_watcher("force_charging_hold")
            elif self.switch_key == "force_discharging":
                duration_min = self._num("force_discharging_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force discharging duration is 0 — set number.alphaess_inverter_force_discharging_duration to a non-zero value")
                await self._start_force_discharging(duration_s)
                if not self._is_on:
                    return
                self._schedule_duration_off(duration_s)
                self._start_battery_power_watcher("force_discharging_hold")
            elif self.switch_key == "force_export":
                duration_min = self._num("force_export_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force export duration is 0 — set number.alphaess_inverter_force_export_duration to a non-zero value")
                await self._start_force_export(duration_s)
                if not self._is_on:
                    return
                self._schedule_duration_off(duration_s)
            elif self.switch_key == "force_import":
                duration_min = self._num("force_import_duration", 120.0)
                duration_s = int(duration_min * 60)
                if duration_s <= 0:
                    raise ValueError("Force import duration is 0 — set number.alphaess_inverter_force_import_duration to a non-zero value")
                await self._start_force_import(duration_s)
                self._schedule_duration_off(duration_s)
                self._start_battery_power_watcher("force_import_hold")
            elif self.switch_key == "dispatch":
                await self._start_dispatch()
            elif self.switch_key == "excess_export":
                await self._start_excess_export()
        except Exception as err:
            _LOGGER.error("Failed to start %s: %s", self.switch_key, err)
            self._is_on = False
            self.async_write_ha_state()

    async def async_apply_param_change(self, *, reset_timer: bool) -> None:
        """Re-apply this switch's dispatch after a mid-run parameter change.

        Called from number._refire_if_active when a dispatch-param slider changes
        while the switch is on. A duration change (reset_timer=True) restarts the
        countdown via the full start sequence; a power or cutoff-SoC change
        (reset_timer=False) rewrites only the setpoint and leaves the countdown,
        auto-off timer and any active watcher running.
        """
        if not self._is_on:
            return
        if reset_timer:
            await self.async_turn_on()
            return
        try:
            if self.switch_key == "force_charging":
                await self._start_force_charging(reset_timer=False)
            elif self.switch_key == "force_discharging":
                duration_s = int(self._num("force_discharging_duration", 120.0) * 60)
                await self._start_force_discharging(duration_s, reset_timer=False)
            elif self.switch_key == "force_export":
                duration_s = int(self._num("force_export_duration", 120.0) * 60)
                await self._start_force_export(duration_s, reset_timer=False)
            elif self.switch_key == "force_import":
                duration_s = int(self._num("force_import_duration", 120.0) * 60)
                await self._start_force_import(duration_s, reset_timer=False)
            elif self.switch_key == "dispatch":
                await self._start_dispatch(reset_timer=False)
        except Exception as err:
            _LOGGER.error("Failed to apply param change for %s: %s", self.switch_key, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.switch_key == "dispatch_pv":
            self._is_on = False
            self.async_write_ha_state()
            await self._maybe_write_pv_switch(DISPATCH_PV_OFF)
            return

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
        if self._fe_listener_unsub:
            self._fe_listener_unsub()
            self._fe_listener_unsub = None
        if self._fi_listener_unsub:
            self._fi_listener_unsub()
            self._fi_listener_unsub = None
        self._ee_last_power_raw = None
        self._ee_last_write_time = 0.0
        self._fe_last_power_raw = None
        self._fe_last_write_time = 0.0
        self._fi_last_power_raw = None
        self._fi_last_write_time = 0.0
        self._bp_near_zero_since = None

    def _schedule_duration_off(self, duration_seconds: int) -> None:
        if self._duration_cancel:
            self._duration_cancel.cancel()
        loop = self.hass.loop

        def _callback():
            task = self.hass.async_create_task(
                self._async_turn_off_silent(),
                name=f"alphaess_{self.switch_key}_duration_off",
            )
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

    def _pv_switch_value(self) -> int:
        """Return the PV switch register value (1 on / 2 off) for the dispatch block.

        Reads the Dispatch PV Enabled switch from the shared switches map; defaults
        to PV on when the switch is missing.
        """
        switches = self.hass.data[DOMAIN].get(f"{self._entry.entry_id}_switches", {})
        pv_sw = switches.get("dispatch_pv")
        return DISPATCH_PV_ON if (pv_sw is None or pv_sw.is_on) else DISPATCH_PV_OFF

    async def _maybe_write_pv_switch(self, value: int) -> None:
        """Apply a PV-switch change to 0x088A while a dispatch is active.

        The single-register write only takes effect during an active dispatch
        (confirmed on real DC-coupled hardware). Outside an active dispatch the
        value is applied as part of the next dispatch fire, and the inverter
        restores PV to normal when the dispatch ends.
        """
        if self._coordinator.active_dispatch_key is not None:
            await self._coordinator.async_write_register(DISPATCH_PV_SWITCH_ADDR, value)

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

    def _start_battery_power_watcher(self, hold_switch_key: str) -> None:
        """Watch power_battery and stop this switch when it stays within +-50 W for 10 s.

        The 10-second window confirms the inverter has reached its SoC target naturally.
        If the Hold switch is on when the window closes, the early stop is skipped and
        the dispatch runs until the duration timer fires.
        """
        if self._soc_unsub:
            self._soc_unsub()
            self._soc_unsub = None
        self._bp_near_zero_since = None

        def _check() -> None:
            if not self._is_on:
                return
            data = self._coordinator.data or {}
            bp = data.get("power_battery")
            if bp is None:
                return
            now = time.monotonic()
            if abs(float(bp)) <= 50:
                if self._bp_near_zero_since is None:
                    self._bp_near_zero_since = now
                elif now - self._bp_near_zero_since >= 10:
                    switches = self.hass.data[DOMAIN].get(
                        f"{self._entry.entry_id}_switches", {}
                    )
                    hold_sw = switches.get(hold_switch_key)
                    if hold_sw and hold_sw.is_on:
                        return
                    self._bp_near_zero_since = None
                    unsub = self._soc_unsub
                    self._soc_unsub = None
                    if unsub:
                        unsub()
                    task = self.hass.async_create_task(
                        self._async_turn_off_silent(),
                        name=f"alphaess_{self.switch_key}_bp_off",
                    )
                    self._pending_tasks.add(task)
                    task.add_done_callback(self._pending_tasks.discard)
            else:
                self._bp_near_zero_since = None

        self._soc_unsub = self._coordinator.async_add_listener(_check)

    # ------------------------------------------------------------------
    # Force Charging
    # ------------------------------------------------------------------

    async def _start_force_charging(self, *, reset_timer: bool = True) -> None:
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
            DISPATCH_FLOW_DIRECTION,
            DISPATCH_PV_UNCHANGED,
        ], reset_timer=reset_timer)
        # reset_timer=False is a mid-run setpoint change: keep the existing
        # countdown and auto-off timer rather than restarting them.
        if reset_timer:
            self._schedule_auto_off(duration_s)

    # ------------------------------------------------------------------
    # Force Discharging
    # ------------------------------------------------------------------

    async def _start_force_discharging(self, duration_s: int, *, reset_timer: bool = True) -> None:
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
            DISPATCH_FLOW_DIRECTION, DISPATCH_PV_UNCHANGED,
        ], reset_timer=reset_timer)

    # ------------------------------------------------------------------
    # Force Export
    # ------------------------------------------------------------------

    def _compute_force_export_power_raw(self, d: dict) -> int | None:
        """Return the dispatch active-power word for Force Export, or None if PV/load unavailable.

        battery_discharge = target_export + house_load - pv (floored at 0); the word is
        the 32000-offset discharge power written at dispatch offset 2.
        """
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            return None
        target_export_w = int(self._num("force_export_power", 5.0) * 1000)
        battery_discharge_w = max(0, target_export_w + int(house_load_w) - int(pv_production_w))
        return int(32000 + battery_discharge_w)

    async def _write_export_dispatch(self, word: int, duration_s: int, *, reset_timer: bool) -> None:
        cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        await self._coordinator.async_write_dispatch([
            1, 0, int(word), 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, duration_s,
            DISPATCH_FLOW_DIRECTION, DISPATCH_PV_UNCHANGED,
        ], reset_timer=reset_timer)

    async def _start_force_export(self, duration_s: int, *, reset_timer: bool = True) -> None:
        d = self._coordinator.data or {}
        soc = d.get("soc_battery")
        cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
        if soc is not None and float(soc) <= cutoff_soc:
            await self._async_turn_off_silent()
            return
        # Seed the servo with the feed-forward estimate. At turn-on the battery is not
        # yet dispatching, so the house-load term is accurate; the watcher takes over
        # with grid-error servoing thereafter.
        power_raw = self._compute_force_export_power_raw(d)
        if power_raw is None:
            # PV/load not yet available; the watcher seeds itself on the next update.
            self._start_force_export_watcher(duration_s)
            return
        await self._write_export_dispatch(power_raw, duration_s, reset_timer=reset_timer)
        self._fe_last_power_raw = power_raw
        self._fe_last_write_time = time.monotonic()
        self._start_force_export_watcher(duration_s)

    def _start_force_export_watcher(self, duration_s: int) -> None:
        """Servo the Force Export battery setpoint on each coordinator update.

        Trims the battery discharge word so the grid meter moves toward -target
        (exporting `target`), using grid error only (see _SERVO_GAIN notes). Rewrites
        use reset_timer=False so the duration countdown is preserved, and are issued
        only when the setpoint moves by _SERVO_DEADBAND_W or every _DISPATCH_STALE_REWRITE_S.
        """
        if self._fe_listener_unsub is not None:
            return

        def _check() -> None:
            if not self._is_on:
                return
            d = self._coordinator.data or {}
            soc = d.get("soc_battery")
            cutoff_soc = self._num("force_export_cutoff_soc", 4.0)
            if soc is not None and float(soc) <= cutoff_soc:
                task = self.hass.async_create_task(
                    self._async_turn_off_silent(),
                    name=f"alphaess_{self.switch_key}_soc_off",
                )
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
                return
            grid = d.get("power_grid")
            if grid is None:
                return
            target_w = int(self._num("force_export_power", 5.0) * 1000)
            if self._fe_last_power_raw is None:
                # No baseline yet (initial feed-forward was deferred). Seed from the
                # feed-forward estimate if available, else assume discharge == target.
                seed = self._compute_force_export_power_raw(d)
                word = seed if seed is not None else int(32000 + max(0, target_w))
            else:
                # Servo: drive grid toward -target by trimming the discharge word.
                # error > 0 means exporting too little, so discharge more.
                error_w = float(grid) + target_w
                new_discharge = (self._fe_last_power_raw - 32000) + _SERVO_GAIN * error_w
                new_discharge = max(0.0, min(float(self._coordinator.ac_limit_w), new_discharge))
                word = int(round(32000 + new_discharge))
            now = time.monotonic()
            changed = (
                self._fe_last_power_raw is None
                or abs(word - self._fe_last_power_raw) >= _SERVO_DEADBAND_W
            )
            stale = (now - self._fe_last_write_time) >= _DISPATCH_STALE_REWRITE_S
            if changed or stale:
                task = self.hass.async_create_task(
                    self._write_export_dispatch(
                        word,
                        int(self._num("force_export_duration", 120.0) * 60),
                        reset_timer=False,
                    ),
                    name=f"alphaess_{self.switch_key}_export_servo",
                )
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
                self._fe_last_power_raw = word
                self._fe_last_write_time = now

        self._fe_listener_unsub = self._coordinator.async_add_listener(_check)

    # ------------------------------------------------------------------
    # Generic Dispatch
    # ------------------------------------------------------------------

    async def _start_dispatch(self, *, reset_timer: bool = True) -> None:
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
            DISPATCH_FLOW_DIRECTION,
            self._pv_switch_value(),
        ], reset_timer=reset_timer)
        # reset_timer=False is a mid-run setpoint change: keep the existing
        # countdown and auto-off timer rather than restarting them.
        if reset_timer:
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
            DISPATCH_FLOW_DIRECTION, DISPATCH_PV_UNCHANGED,
        ])
        self._ee_last_power_raw = power_raw
        self._ee_last_write_time = time.monotonic()
        self._start_ee_watcher()

    def _start_ee_watcher(self) -> None:
        """Subscribe to coordinator updates to auto-pause/resume Excess Export.

        Auto-pause/resume rules for Excess Export:
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
                    self._ee_last_power_raw = None
                    self._ee_last_write_time = 0.0
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
                        if pv_dc > self._coordinator.ac_limit_w:
                            power_raw = max(0, 32000 - (pv_dc - self._coordinator.ac_limit_w))
                        else:
                            power_raw = 32000
                        changed = (
                            self._ee_last_power_raw is None
                            or abs(power_raw - self._ee_last_power_raw) >= 50
                        )
                        stale = (now - self._ee_last_write_time) >= 240
                        if changed or stale:
                            task = self.hass.async_create_task(
                                self._start_excess_export(),
                                name="alphaess_ee_recalc",
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

    def _compute_force_import_power_raw(self, d: dict) -> int | None:
        """Return the dispatch active-power word for Force Import, or None if PV/load unavailable.

        charge_power = target_import - house_load + pv (floored at 0); the word is the
        32000-offset charge power written at dispatch offset 2.
        """
        pv_production_w = _calc_pv_production(d)
        house_load_w = _calc_house_load(d)
        if house_load_w is None or pv_production_w is None:
            return None
        import_power_kw = self._num("force_import_power", 5.0)
        charge_power_w = max(0, int(import_power_kw * 1000) - int(house_load_w) + int(pv_production_w))
        return int(32000 - charge_power_w)

    async def _write_import_dispatch(self, word: int, duration_s: int, *, reset_timer: bool) -> None:
        cutoff_soc = self._num("force_import_cutoff_soc", 100.0)
        soc_raw = int(cutoff_soc / DISPATCH_SOC_SCALE)
        await self._coordinator.async_write_dispatch([
            1, 0, int(word), 0, 32000, DISPATCH_MODE_SOC_CONTROL, soc_raw, 0, duration_s,
            DISPATCH_FLOW_DIRECTION, DISPATCH_PV_UNCHANGED,
        ], reset_timer=reset_timer)

    async def _start_force_import(self, duration_s: int, *, reset_timer: bool = True) -> None:
        d = self._coordinator.data or {}
        # Seed the servo with the feed-forward estimate (accurate at turn-on, before the
        # battery is dispatching); the watcher takes over with grid-error servoing.
        power_raw = self._compute_force_import_power_raw(d)
        if power_raw is None:
            # PV/load not yet available; the watcher seeds itself on the next update.
            self._start_force_import_watcher(duration_s)
            return
        await self._write_import_dispatch(power_raw, duration_s, reset_timer=reset_timer)
        self._fi_last_power_raw = power_raw
        self._fi_last_write_time = time.monotonic()
        self._start_force_import_watcher(duration_s)

    def _start_force_import_watcher(self, duration_s: int) -> None:
        """Servo the Force Import battery setpoint on each coordinator update.

        Trims the battery charge word so the grid meter moves toward +target
        (importing `target`), using grid error only (see _SERVO_GAIN notes). Rewrites
        use reset_timer=False so the duration countdown is preserved, and are issued
        only when the setpoint moves by _SERVO_DEADBAND_W or every _DISPATCH_STALE_REWRITE_S.
        Skips rewrites while fi_paused, matching the previous refresh behaviour.
        """
        if self._fi_listener_unsub is not None:
            return

        def _check() -> None:
            if not self._is_on:
                return
            if self._coordinator.fi_paused:
                return
            d = self._coordinator.data or {}
            grid = d.get("power_grid")
            if grid is None:
                return
            target_w = int(self._num("force_import_power", 5.0) * 1000)
            if self._fi_last_power_raw is None:
                # No baseline yet (initial feed-forward was deferred). Seed from the
                # feed-forward estimate if available, else assume charge == target.
                seed = self._compute_force_import_power_raw(d)
                word = seed if seed is not None else int(32000 - max(0, target_w))
            else:
                # Servo: drive grid toward +target by trimming the charge word.
                # error > 0 means importing too little, so charge more.
                error_w = target_w - float(grid)
                new_charge = (32000 - self._fi_last_power_raw) + _SERVO_GAIN * error_w
                new_charge = max(0.0, min(float(self._coordinator.ac_limit_w), new_charge))
                word = int(round(32000 - new_charge))
            now = time.monotonic()
            changed = (
                self._fi_last_power_raw is None
                or abs(word - self._fi_last_power_raw) >= _SERVO_DEADBAND_W
            )
            stale = (now - self._fi_last_write_time) >= _DISPATCH_STALE_REWRITE_S
            if changed or stale:
                task = self.hass.async_create_task(
                    self._write_import_dispatch(
                        word,
                        int(self._num("force_import_duration", 120.0) * 60),
                        reset_timer=False,
                    ),
                    name=f"alphaess_{self.switch_key}_import_servo",
                )
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)
                self._fi_last_power_raw = word
                self._fi_last_write_time = now

        self._fi_listener_unsub = self._coordinator.async_add_listener(_check)

