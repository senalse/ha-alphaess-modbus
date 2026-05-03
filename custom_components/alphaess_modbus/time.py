from __future__ import annotations

import datetime
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TIME_REGISTERS, ModbusTimeDef
from .coordinator import AlphaESSCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AlphaESSTime(coordinator, entry, reg)
        for reg in TIME_REGISTERS
    )


class AlphaESSTime(CoordinatorEntity[AlphaESSCoordinator], TimeEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        reg: ModbusTimeDef,
    ) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry.entry_id}_{reg.key}"
        self._attr_name = reg.name
        self._attr_icon = reg.icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self) -> datetime.time | None:
        d = self.coordinator.data
        if not d:
            return None
        hour = d.get(f"{self._reg.key}_hour")
        minute = d.get(f"{self._reg.key}_minute")
        if hour is None or minute is None:
            return None
        return datetime.time(int(hour), int(minute))

    async def async_set_value(self, value: datetime.time) -> None:
        d = self.coordinator.data or {}
        old_hour = d.get(f"{self._reg.key}_hour")
        await self.coordinator.async_write_register(self._reg.hour_address, value.hour)
        try:
            await self.coordinator.async_write_register(self._reg.minute_address, value.minute)
        except Exception:
            if old_hour is not None:
                _LOGGER.warning(
                    "Minute write failed for %s; rolling back hour register to %d",
                    self._reg.key,
                    int(old_hour),
                )
                await self.coordinator.async_write_register(
                    self._reg.hour_address, int(old_hour)
                )
            raise
