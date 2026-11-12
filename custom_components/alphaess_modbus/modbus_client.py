from __future__ import annotations

import asyncio
import inspect
import logging
import struct
import time
from typing import Any, Awaitable, Callable

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

# pymodbus renamed the slave keyword: 'slave' in <3.8, 'device_id' in >=3.8
_sig = inspect.signature(AsyncModbusTcpClient.read_holding_registers).parameters
_SLAVE_KWARG = "device_id" if "device_id" in _sig else "slave"

_CONNECT_RETRIES = 2
_CONNECT_RETRY_DELAY = 1.0  # seconds between retries

# Comms-level failures that mean the socket is dead/half-open. pymodbus raises
# ModbusException subclasses (ConnectionException, ModbusIOException) for transport
# errors; protocol errors (e.g. illegal address) are returned via result.isError()
# instead, and do NOT indicate a broken link.
_COMM_ERRORS = (ModbusException, asyncio.TimeoutError, OSError)


class AlphaESSModbusClient:
    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._consecutive_failures: int = 0
        self._skip_until: float = 0.0

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    async def connect(self) -> None:
        """Connect with retries — inverter may refuse immediately after a prior close.

        This wrapper is the single reconnect authority: pymodbus's own background
        reconnect loop is disabled (reconnect_delay=0) so two mechanisms don't fight
        over the inverter's one-connection limit. The previous client is always closed
        before a new one is created, so a reconnect never leaks a socket. Guarded by
        _connect_lock so concurrent callers coalesce into one attempt.
        """
        async with self._connect_lock:
            # Never leak a prior client (and its socket); tear it down first.
            self._teardown_client()
            client = AsyncModbusTcpClient(
                self._host, port=self._port, timeout=5, reconnect_delay=0
            )
            for attempt in range(_CONNECT_RETRIES):
                await client.connect()
                if client.connected:
                    self._client = client
                    return
                if attempt < _CONNECT_RETRIES - 1:
                    _LOGGER.debug(
                        "Connect attempt %d/%d failed, retrying in %.0fs",
                        attempt + 1, _CONNECT_RETRIES, _CONNECT_RETRY_DELAY,
                    )
                    await asyncio.sleep(_CONNECT_RETRY_DELAY)
            # All attempts failed — don't keep a dead client object around.
            try:
                client.close()
            except Exception:  # noqa: BLE001 — close must never raise on the failure path
                pass

    def _teardown_client(self) -> None:
        """Close and forget the current client (synchronous; pymodbus close() is sync)."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    async def close(self) -> None:
        self._teardown_client()

    async def _ensure_connected(self) -> None:
        if not self.connected:
            # Backoff: after 3 consecutive failures hold off reconnects for 10 s so
            # one disconnected cycle doesn't fire dozens of blocking retry loops.
            if time.monotonic() < self._skip_until:
                raise ModbusException("Reconnect backoff active")
            await self.connect()
            if self.connected:
                self._consecutive_failures = 0
            else:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    self._skip_until = time.monotonic() + 10.0
                    _LOGGER.debug(
                        "3 consecutive connect failures — backing off for 10 s"
                    )
        if not self.connected:
            raise ModbusException("Not connected")

    async def _request(
        self, call: Callable[[], Awaitable[Any]], what: str
    ) -> Any:
        """Run one pymodbus request, dropping the connection on a comms failure.

        A raised comms error means the socket is dead or half-open (e.g. after a
        router restart): close it so the next cycle reconnects cleanly instead of
        reusing a zombie connection forever. A returned isError() result is a
        protocol error on a healthy link and leaves the connection intact.
        """
        try:
            result = await call()
        except _COMM_ERRORS as err:
            self._teardown_client()
            raise ModbusException(f"Comm error {what}: {err}") from err
        if result.isError():
            raise ModbusException(f"Error {what}: {result}")
        return result

    async def read_block(self, start: int, count: int) -> list[int]:
        """Read `count` consecutive holding registers starting at `start`.

        Returns a list of raw uint16 values; decoding is done by the caller.
        """
        async with self._lock:
            await self._ensure_connected()
            result = await self._request(
                lambda: self._client.read_holding_registers(
                    start, count=count, **{_SLAVE_KWARG: self._slave_id}
                ),
                f"reading block {start:#06x}+{count}",
            )
            return list(result.registers)

    async def probe(self, slave_id: int, address: int = 0x0102) -> None:
        """Read one register as `slave_id` over this client's connection.

        Used by the reconfigure flow to test new settings against an inverter this
        client is already connected to: the inverter accepts only one TCP
        connection, so a second test client would be refused. Raises
        ModbusException on any failure.
        """
        async with self._lock:
            await self._ensure_connected()
            await self._request(
                lambda: self._client.read_holding_registers(
                    address, count=1, **{_SLAVE_KWARG: slave_id}
                ),
                f"probing {address:#06x} as unit {slave_id}",
            )

    async def read_register(self, address: int, data_type: str, count: int = 1) -> Any:
        async with self._lock:
            return await self._read(address, data_type, count)

    async def _read(self, address: int, data_type: str, count: int) -> Any:
        await self._ensure_connected()

        if data_type == "string":
            result = await self._request(
                lambda: self._client.read_holding_registers(
                    address, count=count, **{_SLAVE_KWARG: self._slave_id}
                ),
                f"reading {address:#06x}",
            )
            raw = b"".join(struct.pack(">H", r) for r in result.registers)
            return raw.decode("ascii", errors="replace").rstrip("\x00")

        reg_count = 2 if data_type in ("int32", "uint32") else 1
        result = await self._request(
            lambda: self._client.read_holding_registers(
                address, count=reg_count, **{_SLAVE_KWARG: self._slave_id}
            ),
            f"reading {address:#06x}",
        )

        regs = result.registers
        if data_type == "int16":
            value = regs[0]
            if value > 32767:
                value -= 65536
        elif data_type == "uint16":
            value = regs[0]
        elif data_type == "int32":
            combined = (regs[0] << 16) | regs[1]
            if combined > 2147483647:
                combined -= 4294967296
            value = combined
        elif data_type == "uint32":
            value = (regs[0] << 16) | regs[1]
        else:
            raise ValueError(f"Unknown data_type: {data_type}")

        return value

    async def write_registers(self, address: int, values: list[int]) -> None:
        async with self._lock:
            await self._ensure_connected()
            await self._request(
                lambda: self._client.write_registers(
                    address, values, **{_SLAVE_KWARG: self._slave_id}
                ),
                f"writing {address:#06x}",
            )

    async def write_register(self, address: int, value: int) -> None:
        async with self._lock:
            await self._ensure_connected()
            await self._request(
                lambda: self._client.write_register(
                    address, value, **{_SLAVE_KWARG: self._slave_id}
                ),
                f"writing {address:#06x}",
            )
