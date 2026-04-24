from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_REGISTERS, ModbusSensorDef
from .coordinator import AlphaESSCoordinator


@dataclass
class CalculatedSensorDef:
    key: str
    name: str
    unit: str
    device_class: str


CALCULATED_SENSORS: list[CalculatedSensorDef] = [
    CalculatedSensorDef("current_pv_production", "Current PV Production", "W", "power"),
    CalculatedSensorDef("current_house_load", "Current House Load", "W", "power"),
]

_DEVICE_CLASS_MAP = {
    "battery": SensorDeviceClass.BATTERY,
    "current": SensorDeviceClass.CURRENT,
    "energy": SensorDeviceClass.ENERGY,
    "frequency": SensorDeviceClass.FREQUENCY,
    "power": SensorDeviceClass.POWER,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "voltage": SensorDeviceClass.VOLTAGE,
}

_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total": SensorStateClass.TOTAL,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
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
        return self.coordinator.data.get(self._reg.key) if self.coordinator.data else None


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

        return None
