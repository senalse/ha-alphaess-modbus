from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DAILY_ENERGY_SENSORS, DOMAIN, SENSOR_REGISTERS, ModbusSensorDef
from .coordinator import AlphaESSCoordinator
from .switch import _calc_house_load, _calc_pv_production


@dataclass
class CalculatedSensorDef:
    key: str
    name: str
    unit: str | None
    device_class: str | None
    state_class: str | None = "measurement"
    icon: str | None = None


CALCULATED_SENSORS: list[CalculatedSensorDef] = [
    CalculatedSensorDef("current_pv_production", "Current PV Production", "W", "power"),
    CalculatedSensorDef("current_house_load", "Current House Load", "W", "power"),
    CalculatedSensorDef("battery_remaining_time", "Battery Remaining Time", "min", "duration"),
    CalculatedSensorDef("inverter_work_mode_name", "Inverter Work Mode Name", None, None,
                        state_class=None, icon="mdi:state-machine"),
]

# Inverter work mode (0x0440) as documented by the vendor register list.
_WORK_MODE_NAMES: dict[int, str] = {
    0: "Wait",
    1: "Online",
    2: "UPS",
    3: "Bypass",
    4: "Fault",
    5: "DC",
    6: "Self Test",
    7: "Check",
    8: "Update Master",
    9: "Update Slave",
    10: "Update ARM",
}

_DEVICE_CLASS_MAP = {
    "battery": SensorDeviceClass.BATTERY,
    "current": SensorDeviceClass.CURRENT,
    "duration": getattr(SensorDeviceClass, "DURATION", None),
    "energy": SensorDeviceClass.ENERGY,
    "energy_storage": getattr(SensorDeviceClass, "ENERGY_STORAGE", None),
    "frequency": SensorDeviceClass.FREQUENCY,
    "power": SensorDeviceClass.POWER,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "voltage": SensorDeviceClass.VOLTAGE,
}

_SENSOR_ENUM_LOOKUPS: dict[str, dict[int, str]] = {
    "dispatch_energy_flow_direction": {
        0: "Aging End",
        1: "PV to Grid",
        2: "PV to Battery",
        3: "Battery to Grid",
        4: "Grid to Battery",
        5: "Battery to Grid 2",
    },
    "ip_method": {0: "DHCP", 1: "Static"},
}

_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total": SensorStateClass.TOTAL,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}


def _fmt_version(v: Any) -> str:
    try:
        n = int(v)
        return f"V{n // 100}.{n % 100:02d}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_ip(v: Any) -> str:
    try:
        n = int(v)
        return f"{(n >> 24) & 0xFF}.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{n & 0xFF}"
    except (TypeError, ValueError):
        return str(v)


_BATTERY_STATUS_MAP: dict[int, str] = {
    0: "Idle",
    1: "Discharging",
    256: "Charging",
    257: "Charging + Discharging",
    512: "Charging (mode 2)",
    513: "Charging (mode 2) + Discharging",
}


def _fmt_battery_status(v: Any) -> str:
    try:
        n = int(v)
        label = _BATTERY_STATUS_MAP.get(n, "Unknown")
        return f"{label} ({n})"
    except (TypeError, ValueError):
        return str(v)


def _fmt_duration_s(v: Any) -> str:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return str(v)
    if n <= 0:
        return "0m"
    hours, remainder = divmod(n, 3600)
    minutes = remainder // 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


_SENSOR_FORMATTERS: dict[str, Callable[[Any], Any]] = {
    "bms_version": _fmt_version,
    "lmu_version": _fmt_version,
    "iso_version": _fmt_version,
    "local_ip": _fmt_ip,
    "subnet_mask": _fmt_ip,
    "gateway": _fmt_ip,
    "battery_status": _fmt_battery_status,
    "dispatch_time": _fmt_duration_s,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        AlphaESSSensor(coordinator, entry, reg) for reg in SENSOR_REGISTERS
    ]
    entities += [
        AlphaESSCalculatedSensor(coordinator, entry, defn) for defn in CALCULATED_SENSORS
    ]
    entities.append(AlphaESSEmsVersionSensor(coordinator, entry))
    entities.append(AlphaESSDispatchCountdownSensor(coordinator, entry))
    entities += [
        AlphaESSModeCountdownSensor(coordinator, entry, switch_key, name, icon)
        for switch_key, name, icon in [
            ("force_charging",    "Force Charging Countdown",    "mdi:battery-charging"),
            ("force_discharging", "Force Discharging Countdown", "mdi:battery-arrow-down"),
            ("force_export",      "Force Export Countdown",      "mdi:transmission-tower-export"),
            ("force_import",      "Force Import Countdown",      "mdi:transmission-tower-import"),
        ]
    ]
    entities += [
        AlphaESSDailySensor(coordinator, entry, key, source_key, ac_power_key)
        for key, source_key, ac_power_key in DAILY_ENERGY_SENSORS
    ]
    async_add_entities(entities)


class AlphaESSSensor(CoordinatorEntity[AlphaESSCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        reg: ModbusSensorDef,
    ) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry.entry_id}_{reg.key}"
        self._attr_name = reg.name
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = _DEVICE_CLASS_MAP.get(reg.device_class or "")
        self._attr_state_class = _STATE_CLASS_MAP.get(reg.state_class or "")
        self._attr_entity_registry_enabled_default = reg.enabled_by_default
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._reg.key)
        lookup = _SENSOR_ENUM_LOOKUPS.get(self._reg.key)
        if lookup is not None and raw is not None:
            return lookup.get(int(raw), str(raw))
        formatter = _SENSOR_FORMATTERS.get(self._reg.key)
        if formatter is not None and raw is not None:
            return formatter(raw)
        return raw

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._reg.key != "battery_status" or not self.coordinator.data:
            return None
        raw = self.coordinator.data.get("battery_status")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            return None
        # High byte = charge state (0, 1 or 2), low byte = discharge state (0 or 1).
        return {"charge_state": (n >> 8) & 0xFF, "discharge_state": n & 0xFF}


class AlphaESSCalculatedSensor(CoordinatorEntity[AlphaESSCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        defn: CalculatedSensorDef,
    ) -> None:
        super().__init__(coordinator)
        self._defn = defn
        self._attr_unique_id = f"{entry.entry_id}_{defn.key}"
        self._attr_name = defn.name
        self._attr_native_unit_of_measurement = defn.unit
        self._attr_device_class = _DEVICE_CLASS_MAP.get(defn.device_class or "")
        self._attr_state_class = _STATE_CLASS_MAP.get(defn.state_class or "")
        if defn.icon:
            self._attr_icon = defn.icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self):
        d = self.coordinator.data
        if not d:
            return None

        if self._defn.key == "current_pv_production":
            return _calc_pv_production(d)

        if self._defn.key == "current_house_load":
            return _calc_house_load(d)

        if self._defn.key == "inverter_work_mode_name":
            mode = d.get("inverter_work_mode")
            if mode is None:
                return None
            n = int(mode)
            return _WORK_MODE_NAMES.get(n, f"Unknown ({n})")

        if self._defn.key == "battery_remaining_time":
            raw = d.get("battery_remaining_time_raw")
            if raw is not None and int(raw) != 0:
                return int(raw)
            soc = d.get("soc_battery")
            capacity = d.get("battery_capacity_kwh")
            power_w = d.get("power_battery")
            if soc is None or capacity is None or power_w is None:
                return None
            soc = float(soc)
            capacity = float(capacity)
            power_w = float(power_w)
            if capacity <= 0 or abs(power_w) < 50:
                return None
            remaining_kwh = (soc / 100.0 * capacity) if power_w < 0 else ((100.0 - soc) / 100.0 * capacity)
            return max(0, int(remaining_kwh / abs(power_w) * 1000.0 * 60.0))

        return None


class AlphaESSCombinedSensor(CoordinatorEntity[AlphaESSCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        keys: list[str],
        name: str,
        unique_id_suffix: str,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._keys = keys
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        parts = [self.coordinator.data.get(k) for k in self._keys]
        if any(p is None for p in parts):
            return None
        return self._format(*parts)

    def _format(self, *parts: Any) -> str:
        raise NotImplementedError


class AlphaESSEmsVersionSensor(AlphaESSCombinedSensor):
    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator, entry,
            keys=["ems_version_high", "ems_version_middle", "ems_version_low", "ems_version_low_suffix"],
            name="EMS Version",
            unique_id_suffix="ems_version",
            icon="mdi:chip",
        )

    def _format(self, high: Any, middle: Any, low: Any, suffix: Any) -> str:
        return f"V{int(high)}.{int(middle)}.{int(low)}{suffix or ''}"


class AlphaESSDispatchCountdownSensor(CoordinatorEntity[AlphaESSCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "dispatch_countdown"

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_dispatch_countdown"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._unsub: Callable | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_track_time_interval(
            self.hass, self._tick, timedelta(seconds=1)
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _tick(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | None:
        started = self.coordinator.dispatch_started_at
        dur = self.coordinator.dispatch_duration_s
        if started is None or dur <= 0:
            return None
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        remaining = max(0, int(dur - elapsed))
        return remaining


class AlphaESSModeCountdownSensor(CoordinatorEntity[AlphaESSCoordinator], SensorEntity):
    """Countdown sensor for a specific dispatch mode (force charging/discharging/export/import)."""
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        switch_key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._switch_key = switch_key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{switch_key}_countdown"
        self._attr_translation_key = f"{switch_key}_countdown"
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._unsub: Callable | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_track_time_interval(self.hass, self._tick, timedelta(seconds=1))

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _tick(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | None:
        if self.coordinator.active_dispatch_key != self._switch_key:
            return None
        started = self.coordinator.dispatch_started_at
        dur = self.coordinator.dispatch_duration_s
        if started is None or dur <= 0:
            return None
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        return max(0, int(dur - elapsed))


class AlphaESSDailySensor(CoordinatorEntity[AlphaESSCoordinator], RestoreSensor):
    """Daily energy sensor that resets at midnight using lifetime totals as a baseline.

    When ac_power_key is set, also integrates that live power register via Riemann
    sum and adds the result to the DC register delta. This handles AC-coupled PV
    inverters, which have no hardware energy counter in the AlphaESS register set.
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        key: str,
        source_key: str,
        ac_power_key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._source_key = source_key
        self._ac_power_key = ac_power_key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._day_start_value: float | None = None
        self._start_date: date | None = None
        self._unsub_midnight: Callable | None = None
        self._ac_accumulated_kwh: float = 0.0
        self._last_ac_time: float | None = None

    def _handle_coordinator_update(self) -> None:
        if self._ac_power_key:
            d = self.coordinator.data or {}
            power_w = d.get(self._ac_power_key)
            now = time.monotonic()
            if power_w is not None and self._last_ac_time is not None:
                elapsed_s = min(now - self._last_ac_time, 60.0)
                self._ac_accumulated_kwh += max(0.0, float(power_w)) * elapsed_s / 3_600_000.0
            self._last_ac_time = now
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        today = date.today()
        last_state = await self.async_get_last_state()
        restored = False
        if last_state and last_state.attributes:
            saved_date_str = last_state.attributes.get("start_date")
            saved_value = last_state.attributes.get("day_start_value")
            if saved_date_str and saved_value is not None:
                try:
                    saved_date = date.fromisoformat(str(saved_date_str))
                    if saved_date == today:
                        self._day_start_value = float(saved_value)
                        self._start_date = saved_date
                        restored = True
                except (ValueError, TypeError):
                    pass

        if not restored:
            current = (self.coordinator.data or {}).get(self._source_key)
            if current is not None:
                self._day_start_value = float(current)
                self._start_date = today

        self._attr_last_reset = dt_util.start_of_local_day()

        if restored and self._ac_power_key and last_state and last_state.attributes:
            saved_ac = last_state.attributes.get("ac_accumulated_kwh")
            if saved_ac is not None:
                try:
                    self._ac_accumulated_kwh = float(saved_ac)
                except (ValueError, TypeError):
                    pass

        self._unsub_midnight = async_track_time_change(
            self.hass, self._reset_day, hour=0, minute=0, second=0
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None

    async def _reset_day(self, _now: datetime) -> None:
        current = (self.coordinator.data or {}).get(self._source_key)
        if current is not None:
            self._day_start_value = float(current)
            self._start_date = date.today()
        self._ac_accumulated_kwh = 0.0
        self._last_ac_time = None
        self._attr_last_reset = dt_util.start_of_local_day()
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        if self._day_start_value is None:
            return None
        current = (self.coordinator.data or {}).get(self._source_key)
        if current is None:
            return None
        dc_kwh = max(0.0, float(current) - self._day_start_value)
        return round(dc_kwh + self._ac_accumulated_kwh, 2)

    @property
    def extra_state_attributes(self) -> dict:
        if self._day_start_value is None:
            return {}
        attrs: dict = {
            "day_start_value": self._day_start_value,
            "start_date": self._start_date.isoformat() if self._start_date else None,
        }
        if self._ac_power_key:
            attrs["ac_accumulated_kwh"] = round(self._ac_accumulated_kwh, 4)
        return attrs
