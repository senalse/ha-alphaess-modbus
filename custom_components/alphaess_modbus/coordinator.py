from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ModbusException

from .const import DOMAIN, SENSOR_REGISTERS, ModbusSensorDef
from .modbus_client import AlphaESSModbusClient

_LOGGER = logging.getLogger(__name__)

# Fastest poll cycle — registers with scan_interval=1 are polled every cycle.
COORDINATOR_INTERVAL = timedelta(seconds=1)


class AlphaESSCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, client: AlphaESSModbusClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=COORDINATOR_INTERVAL,
        )
        self.client = client
        self._last_polled: dict[str, float] = {}

    def _is_due(self, reg: ModbusSensorDef) -> bool:
        last = self._last_polled.get(reg.key, 0.0)
        return (time.monotonic() - last) >= reg.scan_interval

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        now = time.monotonic()

        due = [r for r in SENSOR_REGISTERS if self._is_due(r)]
        if not due:
            return data

        errors: list[str] = []
        for reg in due:
            try:
                raw = await self.client.read_register(reg.address, reg.data_type, reg.count)
                if isinstance(raw, str):
                    value = raw
                else:
                    value = (raw + reg.offset) * reg.scale
                    if reg.precision is not None:
                        value = round(value, reg.precision)
                data[reg.key] = value
                self._last_polled[reg.key] = now
            except ModbusException as err:
                errors.append(f"{reg.key}: {err}")
                _LOGGER.debug("Modbus read error for %s: %s", reg.key, err)

        if errors and not data:
            raise UpdateFailed(f"All reads failed: {errors}")

        return data

    async def async_write_dispatch(self, values: list[int]) -> None:
        from .const import DISPATCH_START_ADDR
        await self.client.write_registers(DISPATCH_START_ADDR, values)
        await self.async_request_refresh()

    async def async_reset_dispatch(self) -> None:
        await self.async_write_dispatch([
            0,      # Dispatch Start: stop
            0, 32000,  # Active Power (32000 offset, hi+lo word)
            0, 32000,  # Reactive Power (32000 offset, hi+lo word)
            0,      # Dispatch Mode
            0,      # Dispatch SoC
            0, 90,  # Dispatch Time (90 seconds)
        ])

    async def async_write_register(self, address: int, value: int) -> None:
        await self.client.write_register(address, value)
        await self.async_request_refresh()

    async def async_write_registers(self, address: int, values: list[int]) -> None:
        await self.client.write_registers(address, values)
        await self.async_request_refresh()

    async def async_sync_datetime(self) -> None:
        import datetime
        now = datetime.datetime.now()
        yy = now.year - 2000
        mm = now.month
        dd = now.day
        hh = now.hour
        mi = now.minute
        ss = now.second
        yymm = int(f"{yy:02x}{mm:02x}", 16)
        ddhh = int(f"{dd:02x}{hh:02x}", 16)
        mmss = int(f"{mi:02x}{ss:02x}", 16)
        await self.client.write_register(0x0740, yymm)
        await asyncio.sleep(0.1)
        await self.client.write_register(0x0741, ddhh)
        await asyncio.sleep(0.1)
        await self.client.write_register(0x0742, mmss)
        await self.async_request_refresh()
