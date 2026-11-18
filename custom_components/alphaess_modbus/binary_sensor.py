from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AlphaESSCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AlphaESSExcessExportPauseSensor(coordinator, entry),
        AlphaESSForceImportPauseSensor(coordinator, entry),
        AlphaESSPeakShavingLimitedSensor(coordinator, entry),
    ])


class AlphaESSExcessExportPauseSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Excess Export Pause"
    _attr_icon = "mdi:pause-circle"
    _attr_translation_key = "excess_export_pause"

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_excess_export_pause"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self._coordinator.ee_paused


class AlphaESSForceImportPauseSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Force Import Pause"
    _attr_icon = "mdi:pause-circle"
    _attr_translation_key = "force_import_pause"

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_force_import_pause"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self._coordinator.fi_paused


class AlphaESSPeakShavingLimitedSensor(BinarySensorEntity):
    """On while Peak Shaving is on, the grid is above the limit and the battery cannot
    discharge more (at its Stop at SoC, the AC limit or the BMS discharge limit)."""
    _attr_has_entity_name = True
    _attr_name = "Peak Shaving Limited"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_translation_key = "peak_shaving_limited"

    def __init__(self, coordinator: AlphaESSCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_peak_shaving_limited"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self._coordinator.ps_limited
