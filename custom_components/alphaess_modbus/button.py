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
        self._key = definition["key"]
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_press(self, **kwargs: Any) -> None:
        if self._key == "dispatch_reset":
            await self._coordinator.async_reset_dispatch()
        elif self._key == "synchronise_date_time":
            await self._coordinator.async_sync_datetime()
