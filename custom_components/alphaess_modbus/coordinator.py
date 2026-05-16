from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ModbusException

from .const import DOMAIN, SENSOR_REGISTERS, ModbusSensorDef, B3_SCALE_OVERRIDES
from .modbus_client import AlphaESSModbusClient

_LOGGER = logging.getLogger(__name__)

# Fast SOC sampling rate (seconds) used while a SOC watcher is active.
_SOC_FAST_INTERVAL = 2
_SOC_BATTERY_KEY = "soc_battery"

# Per-register scan intervals — used for stale-entry expiry.
_SCAN_INTERVAL_MAP: dict[str, float] = {r.key: r.scan_interval for r in SENSOR_REGISTERS}


def _reg_width(reg: ModbusSensorDef) -> int:
    return 2 if reg.data_type in ("int32", "uint32") else 1


def _group_registers(
    regs: list[ModbusSensorDef],
) -> list[tuple[int, int, list[ModbusSensorDef]]]:
    """Group numeric (non-string) registers into (start, count, members) block tuples.

    Adjacent registers (gap <= 4) are merged so one read_block call covers the span.
    Each group is capped at 100 registers to stay within inverter limits.
    """
    if not regs:
        return []
    sorted_regs = sorted(regs, key=lambda r: r.address)
    groups: list[tuple[int, int, list[ModbusSensorDef]]] = []
    g_start = sorted_regs[0].address
    g_end = g_start + _reg_width(sorted_regs[0]) - 1
    g_regs: list[ModbusSensorDef] = [sorted_regs[0]]

    for reg in sorted_regs[1:]:
        r_end = reg.address + _reg_width(reg) - 1
        # Merge if gap <= 4 registers and total span stays within 100
        if reg.address <= g_end + 5 and r_end - g_start + 1 <= 100:
            g_regs.append(reg)
            g_end = max(g_end, r_end)
        else:
            groups.append((g_start, g_end - g_start + 1, g_regs))
            g_start = reg.address
            g_end = r_end
            g_regs = [reg]

    groups.append((g_start, g_end - g_start + 1, g_regs))
    return groups


def _decode_block(reg: ModbusSensorDef, raw: list[int], offset: int) -> Any:
    """Decode a register value from a raw uint16 word slice (block read result)."""
    dt = reg.data_type
    if dt == "int16":
        v: int = raw[offset]
        if v > 32767:
            v -= 65536
    elif dt == "uint16":
        v = raw[offset]
    elif dt == "int32":
        combined = (raw[offset] << 16) | raw[offset + 1]
        if combined > 2147483647:
            combined -= 4294967296
        v = combined
    elif dt == "uint32":
        v = (raw[offset] << 16) | raw[offset + 1]
    else:
        raise ValueError(f"Block decode: unsupported type {dt!r}")
    value = (v + reg.offset) * reg.scale
    if reg.precision is not None:
        value = round(value, reg.precision)
        if reg.precision == 0:
            value = int(value)
    return value


class AlphaESSCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, client: AlphaESSModbusClient) -> None:
        options = config_entry.options
        poll_mode = options.get("poll_mode", "normal")
        if poll_mode == "slow":
            self._scan_multiplier: float = float(options.get("slow_multiplier", 3.0))
            loop_interval = 2
        elif poll_mode == "fast":
            self._scan_multiplier = float(options.get("fast_multiplier", 0.5))
            loop_interval = 1
        else:
            self._scan_multiplier = 1.0
            loop_interval = 2
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=loop_interval),
        )
        self._model_variant: str = options.get("model_variant", "standard")
        self.client = client
        self._last_polled: dict[str, float] = {}
        self._fast_soc_refcount: int = 0
        # Caches for number/select entity values — populated by those entities
        # so switch.py can read them without going through hass.states.
        self.numbers: dict[str, float] = {}
        self.selects: dict[str, str] = {}
        self.ac_limit_w: int = 20000  # updated by inverter_ac_limit select entity
        self.ee_paused: bool = False
        self.fi_paused: bool = False
        self.dispatch_started_at: datetime | None = None
        self.dispatch_duration_s: int = 0
        self.active_dispatch_key: str | None = None

    def get_number(self, key: str) -> float | None:
        return self.numbers.get(key)

    def get_select(self, key: str) -> str | None:
        return self.selects.get(key)

    def set_fast_soc(self, enabled: bool) -> None:
        """Increment or decrement the fast-SOC refcount.

        While refcount > 0, soc_battery is sampled every 2 s instead of its
        default 10 s interval. Multiple concurrent watchers coexist safely.
        """
        if enabled:
            self._fast_soc_refcount += 1
        else:
            self._fast_soc_refcount = max(0, self._fast_soc_refcount - 1)

    def _is_due(self, reg: ModbusSensorDef) -> bool:
        last = self._last_polled.get(reg.key, 0.0)
        if reg.key == _SOC_BATTERY_KEY and self._fast_soc_refcount > 0:
            interval: float = _SOC_FAST_INTERVAL
        else:
            interval = reg.scan_interval * self._scan_multiplier
        return (time.monotonic() - last) >= interval

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        now = time.monotonic()

        due = [r for r in SENSOR_REGISTERS if self._is_due(r)]
        if not due:
            return data

        string_regs = [r for r in due if r.data_type == "string"]
        numeric_regs = [r for r in due if r.data_type != "string"]
        errors: list[str] = []
        errors_this_cycle = 0

        # Block reads for numeric registers
        for g_start, g_count, g_regs in _group_registers(numeric_regs):
            if errors_this_cycle > 5:
                raise UpdateFailed(
                    f"Too many read errors this cycle ({errors_this_cycle}), aborting"
                )
            try:
                raw = await self.client.read_block(g_start, g_count)
                for reg in g_regs:
                    offset = reg.address - g_start
                    try:
                        value = _decode_block(reg, raw, offset)
                        if self._model_variant == "b3" and reg.key in B3_SCALE_OVERRIDES:
                            v_raw = raw[offset]
                            if reg.data_type == "int16" and v_raw > 32767:
                                v_raw -= 65536
                            elif reg.data_type == "int32":
                                v_raw = (raw[offset] << 16) | raw[offset + 1]
                                if v_raw > 2147483647:
                                    v_raw -= 4294967296
                            value = (v_raw + reg.offset) * B3_SCALE_OVERRIDES[reg.key]
                            if reg.precision is not None:
                                value = round(value, reg.precision)
                                if reg.precision == 0:
                                    value = int(value)
                        data[reg.key] = value
                        self._last_polled[reg.key] = now
                    except Exception as decode_err:
                        errors.append(f"{reg.key}: decode error: {decode_err}")
                        errors_this_cycle += 1
                        _LOGGER.debug("Decode error for %s: %s", reg.key, decode_err)
            except ModbusException as err:
                errors_this_cycle += 1
                for reg in g_regs:
                    errors.append(f"{reg.key}: {err}")
                _LOGGER.debug("Block read error at %#06x+%d: %s", g_start, g_count, err)

        # Individual reads for string registers
        for reg in string_regs:
            if errors_this_cycle > 5:
                raise UpdateFailed(
                    f"Too many read errors this cycle ({errors_this_cycle}), aborting"
                )
            try:
                data[reg.key] = await self.client.read_register(
                    reg.address, reg.data_type, reg.count
                )
                self._last_polled[reg.key] = now
            except ModbusException as err:
                errors_this_cycle += 1
                errors.append(f"{reg.key}: {err}")
                _LOGGER.debug("Modbus read error for %s: %s", reg.key, err)

        if errors and not data:
            raise UpdateFailed(f"All reads failed: {errors}")

        # Expire entries not successfully read for more than 5x their scan interval.
        # Sensors whose register permanently fails will report unknown instead of
        # keeping the last good value indefinitely.
        for key in list(data.keys()):
            last = self._last_polled.get(key, 0.0)
            if last == 0.0:
                continue
            si = _SCAN_INTERVAL_MAP.get(key)
            if si and (now - last) > 5 * si:
                del data[key]

        return data

    async def async_write_dispatch(self, values: list[int]) -> None:
        from .const import DISPATCH_START_ADDR
        await self.client.write_registers(DISPATCH_START_ADDR, values)
        if values and values[0] == 1 and len(values) >= 9:
            self.dispatch_started_at = datetime.now(timezone.utc)
            self.dispatch_duration_s = int(values[8])
        else:
            self.dispatch_started_at = None
            self.dispatch_duration_s = 0

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

    async def async_write_raw(self, address: int, value: int) -> None:
        _LOGGER.debug("write_raw: address=%#06x value=%d", address, value)
        await self.client.write_register(address, value)

    async def async_write_registers(self, address: int, values: list[int]) -> None:
        await self.client.write_registers(address, values)

    async def async_sync_datetime(self) -> None:
        import datetime
        now = datetime.datetime.now()
        yy = now.year - 2000
        # BCD-encoded uint16: each byte holds a decimal field packed as hex digits,
        # e.g. year=26, month=5 -> 0x2605. Confirmed correct on this inverter;
        # raw binary encoding (year * 256 + month) produces wrong values.
        yymm = int(f"{yy:02x}{now.month:02x}", 16)
        ddhh = int(f"{now.day:02x}{now.hour:02x}", 16)
        mmss = int(f"{now.minute:02x}{now.second:02x}", 16)
        await self.client.write_registers(0x0740, [yymm, ddhh, mmss])
        await self.async_request_refresh()
