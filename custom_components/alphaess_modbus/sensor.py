from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_REGISTERS, ModbusSensorDef
from .coordinator import AlphaESSCoordinator


@dataclass
class CalculatedSensorDef:
    key: str
    name: str
    unit: str
    device_class: str | None


CALCULATED_SENSORS: list[CalculatedSensorDef] = [
    CalculatedSensorDef("current_pv_production", "Current PV Production", "W", "power"),
    CalculatedSensorDef("current_house_load", "Current House Load", "W", "power"),
    CalculatedSensorDef("battery_remaining_time", "Battery Remaining Time", "min", "duration"),
]

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
        self._attr_device_class = _DEVICE_CLASS_MAP.get(defn.device_class)
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    def _pv_production(self, d: dict) -> int | None:
        keys = ["pv1_power", "pv2_power", "pv3_power", "pv4_power", "active_power_pv_meter"]
        if any(d.get(k) is None for k in keys):
            return None
        return max(0, sum(int(d[k]) for k in keys))

    @property
    def native_value(self):
        d = self.coordinator.data
        if not d:
            return None

        if self._defn.key == "current_pv_production":
            return self._pv_production(d)

        if self._defn.key == "current_house_load":
            grid = d.get("power_grid")
            if grid is None:
                return None
            if float(d.get("inverter_work_mode", 0)) == 2:
                return round(float(grid))
            pv = self._pv_production(d)
            battery = d.get("power_battery")
            if pv is None or battery is None:
                return None
            return max(0, int(pv) + int(battery) + int(grid))

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
    _attr_native_unit_of_measurement = "s"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "dispatch_countdown"

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_name = "Dispatch Time Remaining"
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
    """Countdown sensor for a specific dispatch mode (force charging/discharging/export/import).

    Shows the live dispatch_time register value when that mode is active, zero otherwise.
    """
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "s"
    _attr_device_class = None
    _attr_state_class = None

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

    @property
    def native_value(self) -> int:
        if self.coordinator.active_dispatch_key != self._switch_key:
            return 0
        dispatch_time = (self.coordinator.data or {}).get("dispatch_time", 0)
        return int(dispatch_time)
