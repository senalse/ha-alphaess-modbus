from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)


class AlphaESSModbusClient:
    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        self._client = AsyncModbusTcpClient(self._host, port=self._port)
        return await self._client.connect()

    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    async def read_register(self, address: int, data_type: str, count: int = 1) -> Any:
        async with self._lock:
            return await self._read(address, data_type, count)

    async def _read(self, address: int, data_type: str, count: int) -> Any:
        if self._client is None or not self._client.connected:
            raise ModbusException("Not connected")

        if data_type == "string":
            result = await self._client.read_holding_registers(address, count=count, slave=self._slave_id)
            if result.isError():
                raise ModbusException(f"Error reading {address:#06x}: {result}")
            raw = b"".join(struct.pack(">H", r) for r in result.registers)
            return raw.decode("ascii", errors="replace").rstrip("\x00")

        reg_count = 2 if data_type in ("int32", "uint32") else 1
        result = await self._client.read_holding_registers(address, count=reg_count, slave=self._slave_id)
        if result.isError():
            raise ModbusException(f"Error reading {address:#06x}: {result}")

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
            if self._client is None or not self._client.connected:
                raise ModbusException("Not connected")
            result = await self._client.write_registers(address, values, slave=self._slave_id)
            if result.isError():
                raise ModbusException(f"Error writing {address:#06x}: {result}")

    async def write_register(self, address: int, value: int) -> None:
        await self.write_registers(address, [value])
