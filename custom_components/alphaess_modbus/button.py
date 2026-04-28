from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RESET_MODE_ADDR
from .coordinator import AlphaESSCoordinator

_LOGGER = logging.getLogger(__name__)

BUTTON_DEFS = [
    {
        "key": "dispatch_reset",
        "name": "Dispatch Reset",
        "icon": "mdi:restart",
    },
    {
        "key": "synchronise_date_time",
        "name": "Synchronise Date & Time",
        "icon": "mdi:clock-check-outline",
    },
    {
        "key": "sync_dispatch_state",
        "name": "Sync Dispatch State",
        "icon": "mdi:sync",
    },
    {
        "key": "restart_pcs",
        "name": "Restart PCS",
        "icon": "mdi:restart",
    },
    {
        "key": "restart_ems",
        "name": "Restart EMS",
        "icon": "mdi:restart",
    },
    {
        "key": "reset_energy_totals",
        "name": "Reset Energy Totals",
        "icon": "mdi:counter",
    },
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AlphaESSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AlphaESSButton(coordinator, entry, d) for d in BUTTON_DEFS
    )


class AlphaESSButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaESSCoordinator,
        entry: ConfigEntry,
        definition: dict,
    ) -> None:
        self._coordinator = coordinator
        self._entry_id = entry.entry_id
        self._key = definition["key"]
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_name = definition["name"]
        self._attr_translation_key = self._key
        self._attr_icon = definition["icon"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_press(self, **kwargs: Any) -> None:
        if self._key == "dispatch_reset":
            await self._coordinator.async_reset_dispatch()
        elif self._key == "synchronise_date_time":
            await self._coordinator.async_sync_datetime()
        elif self._key == "sync_dispatch_state":
            await self._sync_dispatch_state()
        elif self._key == "restart_pcs":
            await self._coordinator.async_write_register(RESET_MODE_ADDR, 7)
        elif self._key == "restart_ems":
            await self._coordinator.async_write_register(RESET_MODE_ADDR, 8)
        elif self._key == "reset_energy_totals":
            await self._coordinator.async_write_register(RESET_MODE_ADDR, 1)

    async def _sync_dispatch_state(self) -> None:
        from .switch import _MUTEX_SWITCHES

        switches = self.hass.data[DOMAIN].get(f"{self._entry_id}_switches", {})
        dispatch_on = bool(
            self._coordinator.data
            and self._coordinator.data.get("dispatch_start") == 1
        )
        any_on = any(sw.is_on for key, sw in switches.items() if key in _MUTEX_SWITCHES)

        if dispatch_on and not any_on:
            # Infer which switch to mark based on active power direction
            power = (self._coordinator.data or {}).get("dispatch_active_power", 0)
            if power > 0:
                inferred_key = "force_export"
            elif power < 0:
                inferred_key = "force_charging"
            else:
                inferred_key = "dispatch"
            sw = switches.get(inferred_key)
            if sw:
                sw._is_on = True
                sw.async_write_ha_state()
                _LOGGER.info("sync_dispatch_state: dispatch active (power=%s W), marked %s on", power, inferred_key)
        elif not dispatch_on:
            # Inverter dispatch is off — clear any switches still showing on in HA
            cleared = []
            for key, sw in switches.items():
                if sw.is_on:
                    sw._is_on = False
                    sw.async_write_ha_state()
                    cleared.append(key)
            if cleared:
                _LOGGER.info("sync_dispatch_state: cleared stale on-state for %s", cleared)
