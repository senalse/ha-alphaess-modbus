"""
Diagnostic script: mirrors exactly what the HA integration does.

Usage:
    python tools/test_connection.py --host 10.0.0.209
    python tools/test_connection.py --host 10.0.0.209 --port 502 --slave 85
"""
import argparse
import asyncio
import traceback
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

DEFAULT_HOST  = "10.0.0.209"
DEFAULT_PORT  = 502
DEFAULT_SLAVE = 85


async def test_async_connect(host: str, port: int, slave: int) -> None:
    print(f"\n=== Test 1: AsyncModbusTcpClient (same as integration) ===")
    client = AsyncModbusTcpClient(host, port=port, timeout=5)
    print(f"  connect() ...")
    result = await client.connect()
    print(f"  connect() returned: {result!r}")
    print(f"  client.connected:   {client.connected!r}")

    if not client.connected:
        print("  FAIL: not connected after connect()")
        return

    print(f"  Reading 0x0102 (SoC) slave={slave} ...")
    try:
        r = await client.read_holding_registers(0x0102, count=1, device_id=slave)
        print(f"  isError(): {r.isError()}")
        if not r.isError():
            print(f"  registers: {r.registers}  => SOC {r.registers[0] * 0.1:.1f}%")
        else:
            print(f"  Modbus error response: {r}")
    except Exception as e:
        print(f"  EXCEPTION during read: {type(e).__name__}: {e}")
        traceback.print_exc()

    client.close()


async def test_async_read_battery(host: str, port: int, slave: int) -> None:
    print(f"\n=== Test 2: AsyncModbusTcpClient reading battery registers ===")
    client = AsyncModbusTcpClient(host, port=port, timeout=5)
    await client.connect()
    if not client.connected:
        print("  FAIL: could not connect")
        return

    for addr, count, label in [
        (0x0100, 2, "Voltage + Current"),
        (0x0102, 1, "SOC"),
    ]:
        try:
            r = await client.read_holding_registers(addr, count=count, device_id=slave)
            if r.isError():
                print(f"  {label} @ {addr:#06x}: ERROR {r}")
            else:
                print(f"  {label} @ {addr:#06x}: {r.registers}")
        except Exception as e:
            print(f"  {label} @ {addr:#06x}: EXCEPTION {type(e).__name__}: {e}")

    client.close()


async def test_no_slave(host: str, port: int) -> None:
    print(f"\n=== Test 3: Same but with device_id=1 (wrong slave, for comparison) ===")
    client = AsyncModbusTcpClient(host, port=port, timeout=5)
    await client.connect()
    if not client.connected:
        print("  FAIL: could not connect")
        return

    try:
        r = await client.read_holding_registers(0x0102, count=1, device_id=1)
        print(f"  device_id=1 response: isError={r.isError()}, raw={r}")
    except Exception as e:
        print(f"  device_id=1 EXCEPTION: {type(e).__name__}: {e}")

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaESS Modbus connection diagnostic")
    parser.add_argument("--host",  default=DEFAULT_HOST,  help=f"Inverter IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port",  default=DEFAULT_PORT,  type=int)
    parser.add_argument("--slave", default=DEFAULT_SLAVE, type=int)
    args = parser.parse_args()

    asyncio.run(test_async_connect(args.host, args.port, args.slave))
    asyncio.run(test_async_read_battery(args.host, args.port, args.slave))
    asyncio.run(test_no_slave(args.host, args.port))


if __name__ == "__main__":
    main()
