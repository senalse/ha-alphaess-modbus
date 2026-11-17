from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.exceptions import ModbusException

from .const import (
    DOMAIN,
    SENSOR_REGISTERS,
    ModbusSensorDef,
    B3_SCALE_OVERRIDES,
    DISPATCH_FLOW_DIRECTION,
    DISPATCH_PV_UNCHANGED,
)
from .modbus_client import AlphaESSModbusClient, ModbusIllegalAddress

_LOGGER = logging.getLogger(__name__)

# Per-register scan intervals — used for stale-entry expiry.
_SCAN_INTERVAL_MAP: dict[str, float] = {r.key: r.scan_interval for r in SENSOR_REGISTERS}

# A register that answers "illegal data address" (Modbus exception code 2) this many
# times in a row is treated as not implemented on this model: it is taken out of the
# block reads (so it cannot fail its neighbours) and only retried on its own every
# _UNSUPPORTED_RETRY_S. Any successful read puts it back on its normal schedule.
_UNSUPPORTED_AFTER = 3
_UNSUPPORTED_RETRY_S = 600.0


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
            loop_interval = self._scan_multiplier
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
        # When Excess Export will turn itself off (None = no duration set or not running)
        self.ee_off_at: datetime | None = None
        # Registers this model does not implement (exception code 2): key -> monotonic
        # time of the next single retry. _illegal_counts tracks consecutive code-2 replies.
        self._unsupported: dict[str, float] = {}
        self._illegal_counts: dict[str, int] = {}

    def get_number(self, key: str) -> float | None:
        return self.numbers.get(key)

    def get_select(self, key: str) -> str | None:
        return self.selects.get(key)

    def _is_due(self, reg: ModbusSensorDef) -> bool:
        retry_at = self._unsupported.get(reg.key)
        if retry_at is not None:
            return time.monotonic() >= retry_at
        last = self._last_polled.get(reg.key, 0.0)
        interval = reg.scan_interval * self._scan_multiplier
        return (time.monotonic() - last) >= interval

    def _store(self, data: dict[str, Any], reg: ModbusSensorDef, raw: list[int], offset: int, now: float) -> None:
        """Decode one register from a raw block and record it as freshly polled."""
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
        self._illegal_counts.pop(reg.key, None)
        if self._unsupported.pop(reg.key, None) is not None:
            _LOGGER.debug("Register %s (%#06x) answered again; polling it normally", reg.key, reg.address)

    def _note_illegal(self, reg: ModbusSensorDef, now: float) -> None:
        """Count a code-2 reply; after _UNSUPPORTED_AFTER in a row, back the register off."""
        if reg.key in self._unsupported:
            self._unsupported[reg.key] = now + _UNSUPPORTED_RETRY_S
            return
        count = self._illegal_counts.get(reg.key, 0) + 1
        self._illegal_counts[reg.key] = count
        if count >= _UNSUPPORTED_AFTER:
            self._unsupported[reg.key] = now + _UNSUPPORTED_RETRY_S
            _LOGGER.debug(
                "Register %s (%#06x) is not supported by this inverter (exception code 2); "
                "retrying it every %d s",
                reg.key, reg.address, int(_UNSUPPORTED_RETRY_S),
            )

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        now = time.monotonic()

        due = [r for r in SENSOR_REGISTERS if self._is_due(r)]
        if not due:
            return data

        string_regs = [r for r in due if r.data_type == "string"]
        numeric_regs = [r for r in due if r.data_type != "string"]
        # Registers known to be unsupported are retried on their own so they can
        # never fail a block of registers that do exist on this model.
        retry_regs = [r for r in numeric_regs if r.key in self._unsupported]
        block_regs = [r for r in numeric_regs if r.key not in self._unsupported]
        errors: list[str] = []
        errors_this_cycle = 0

        groups = _group_registers(block_regs) + [
            (r.address, _reg_width(r), [r]) for r in retry_regs
        ]

        # Block reads for numeric registers
        for g_start, g_count, g_regs in groups:
            if errors_this_cycle > 5:
                raise UpdateFailed(
                    f"Too many read errors this cycle ({errors_this_cycle}), aborting"
                )
            try:
                raw = await self.client.read_block(g_start, g_count)
            except ModbusIllegalAddress as err:
                # Not a link or inverter fault: some address in the span does not
                # exist on this model. Find out which by reading members one by one.
                _LOGGER.debug("Block read error at %#06x+%d: %s", g_start, g_count, err)
                if len(g_regs) == 1:
                    self._note_illegal(g_regs[0], now)
                    continue
                for reg in g_regs:
                    try:
                        single = await self.client.read_block(reg.address, _reg_width(reg))
                        self._store(data, reg, single, 0, now)
                    except ModbusIllegalAddress:
                        self._note_illegal(reg, now)
                    except ModbusException as single_err:
                        errors_this_cycle += 1
                        errors.append(f"{reg.key}: {single_err}")
                        _LOGGER.debug("Modbus read error for %s: %s", reg.key, single_err)
                    except Exception as decode_err:
                        errors.append(f"{reg.key}: decode error: {decode_err}")
                        errors_this_cycle += 1
                        _LOGGER.debug("Decode error for %s: %s", reg.key, decode_err)
                continue
            except ModbusException as err:
                errors_this_cycle += 1
                for reg in g_regs:
                    errors.append(f"{reg.key}: {err}")
                _LOGGER.debug("Block read error at %#06x+%d: %s", g_start, g_count, err)
                continue
            for reg in g_regs:
                try:
                    self._store(data, reg, raw, reg.address - g_start, now)
                except Exception as decode_err:
                    errors.append(f"{reg.key}: decode error: {decode_err}")
                    errors_this_cycle += 1
                    _LOGGER.debug("Decode error for %s: %s", reg.key, decode_err)

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
                self._illegal_counts.pop(reg.key, None)
                self._unsupported.pop(reg.key, None)
            except ModbusIllegalAddress as err:
                _LOGGER.debug("Modbus read error for %s: %s", reg.key, err)
                self._note_illegal(reg, now)
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

    async def async_write_dispatch(self, values: list[int], *, reset_timer: bool = True) -> None:
        from .const import DISPATCH_START_ADDR
        await self.client.write_registers(DISPATCH_START_ADDR, values)
        if values and values[0] == 1 and len(values) >= 9:
            if reset_timer:
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
            DISPATCH_FLOW_DIRECTION,  # Flow Direction (0x0889)
            DISPATCH_PV_UNCHANGED,    # PV Switch (0x088A): leave unchanged on stop
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
