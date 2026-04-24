from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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

    async def _sync_dispatch_state(self) -> None:
        from .switch import _MUTEX_SWITCHES

        switches = self.hass.data[DOMAIN].get(f"{self._entry_id}_switches", {})
        dispatch_on = bool(
            self._coordinator.data
            and self._coordinator.data.get("dispatch_start") == 1
        )
        any_on = any(sw.is_on for key, sw in switches.items() if key in _MUTEX_SWITCHES)

        if dispatch_on and not any_on:
            # Dispatch running on inverter but no switch claims it — mark generic dispatch as on
            sw = switches.get("dispatch")
            if sw:
                sw._is_on = True
                sw.async_write_ha_state()
                _LOGGER.info("sync_dispatch_state: dispatch active on inverter, marked dispatch switch on")
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
