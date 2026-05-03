"""
AlphaESS Modbus register scanner.

Scans holding-register ranges on the inverter, recording which addresses
respond and what raw values they hold.  Results are written to
scan_results.csv and also printed to stdout.

IMPORTANT: The AlphaESS inverter only allows ONE TCP connection at a time.
Stop the Home Assistant integration (or disable the integration) before
running this, otherwise reads will fail.

Usage:
    python tools/scan_registers.py
    python tools/scan_registers.py --host 10.0.0.209 --slave 85 --chunk 16
"""

import argparse
import asyncio
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow importing the integration package from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))
from custom_components.alphaess_modbus.const import SENSOR_REGISTERS  # noqa: E402

from pymodbus.client import AsyncModbusTcpClient

HOST    = "10.0.0.209"
PORT    = 502
SLAVE   = 85
TIMEOUT = 5
CHUNK   = 16    # registers per bulk read (max 125, but smaller = fewer wasted reads)
DELAY   = 0.08  # seconds between chunk requests - be kind to the inverter

# ---------------------------------------------------------------------------
# Register ranges to scan  (start_addr, end_addr_inclusive)
# Covers all known clusters plus the gaps between them.
# ---------------------------------------------------------------------------
SCAN_RANGES = [
    (0x0000, 0x00FF),   # grid meter, energy totals, power
    (0x0100, 0x01FF),   # battery
    (0x0200, 0x03FF),   # unknown gap - may contain EMS / grid info
    (0x0400, 0x04FF),   # inverter power, PV strings, version strings start
    (0x0500, 0x05FF),   # unknown
    (0x0600, 0x06FF),   # version strings
    (0x0700, 0x07FF),   # EMS version, system time
    (0x0800, 0x08FF),   # settings: charging, dispatch, network
    (0x0900, 0x0FFF),   # unknown - potentially large gap
    (0x1000, 0x10FF),   # grid safety / protection thresholds
]


def _build_known() -> dict[int, str]:
    """Build address->label map from the integration's SENSOR_REGISTERS."""
    known: dict[int, str] = {}
    for reg in SENSOR_REGISTERS:
        if reg.address is None:
            continue
        if reg.data_type in ("int32", "uint32"):
            known[reg.address]     = f"{reg.key} (HI)"
            known[reg.address + 1] = f"{reg.key} (LO)"
        elif reg.data_type == "string":
            for i in range(reg.count or 1):
                known[reg.address + i] = f"{reg.key} (s{i})"
        else:
            known[reg.address] = reg.key
    return known


KNOWN = _build_known()


@dataclass
class RegisterResult:
    address: int
    raw: int
    known_label: str | None


async def scan(host: str, port: int, slave: int, chunk: int) -> list[RegisterResult]:
    client = AsyncModbusTcpClient(host, port=port, timeout=TIMEOUT)
    print(f"Connecting to {host}:{port} slave={slave} ...")
    await client.connect()
    if not client.connected:
        print("ERROR: could not connect. Is HA stopped / integration disabled?", file=sys.stderr)
        sys.exit(1)
    print("Connected.\n")

    results: list[RegisterResult] = []
    total_chunks = sum((end - start + 1 + chunk - 1) // chunk
                       for start, end in SCAN_RANGES)
    done = 0

    for range_start, range_end in SCAN_RANGES:
        addr = range_start
        while addr <= range_end:
            count = min(chunk, range_end - addr + 1)
            resp = await client.read_holding_registers(addr, count=count, device_id=slave)

            if resp.isError():
                for single in range(addr, addr + count):
                    await asyncio.sleep(DELAY)
                    r = await client.read_holding_registers(single, count=1, device_id=slave)
                    if not r.isError():
                        results.append(RegisterResult(
                            single, r.registers[0], KNOWN.get(single)
                        ))
            else:
                for i, raw in enumerate(resp.registers):
                    a = addr + i
                    results.append(RegisterResult(a, raw, KNOWN.get(a)))

            addr += count
            done += 1
            pct = done * 100 // total_chunks
            print(f"\r  {pct:3d}%  scanning {addr - count:#06x}-{addr - 1:#06x}  "
                  f"({done}/{total_chunks} chunks)", end="", flush=True)
            await asyncio.sleep(DELAY)

    print()
    client.close()
    return results


def write_results(results: list[RegisterResult], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["address_hex", "address_dec", "raw_uint16", "raw_int16",
                         "raw_hex", "known_label", "note"])
        for r in results:
            int16 = r.raw if r.raw <= 32767 else r.raw - 65536
            note = "" if r.known_label else "*** UNKNOWN ***"
            writer.writerow([
                f"0x{r.address:04X}",
                r.address,
                r.raw,
                int16,
                f"0x{r.raw:04X}",
                r.known_label or "",
                note,
            ])


def print_summary(results: list[RegisterResult]) -> None:
    total   = len(results)
    known   = sum(1 for r in results if r.known_label)
    unknown = total - known

    print(f"\n{'='*70}")
    print(f"  Scan complete: {total} registers responded")
    print(f"  Known   : {known}")
    print(f"  Unknown : {unknown}")
    print(f"{'='*70}")

    if unknown:
        print(f"\nUnknown registers (potentially new/undocumented):\n")
        print(f"  {'Address':<10}  {'Raw (uint16)':<14}  {'Raw (int16)':<13}  Raw hex")
        print(f"  {'-'*8:<10}  {'-'*12:<14}  {'-'*11:<13}  -------")
        for r in results:
            if not r.known_label:
                int16 = r.raw if r.raw <= 32767 else r.raw - 65536
                print(f"  {f'0x{r.address:04X}':<10}  {r.raw:<14}  {int16:<13}  0x{r.raw:04X}")


async def main(args: argparse.Namespace) -> None:
    results = await scan(args.host, args.port, args.slave, args.chunk)

    out = "scan_results.csv"
    write_results(results, out)
    print(f"\nFull results saved to: {out}")
    print_summary(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlphaESS Modbus register scanner")
    parser.add_argument("--host",  default=HOST,  help=f"Inverter IP (default: {HOST})")
    parser.add_argument("--port",  default=PORT,  type=int)
    parser.add_argument("--slave", default=SLAVE, type=int)
    parser.add_argument("--chunk", default=CHUNK, type=int,
                        help="Registers per bulk read (default 16)")
    asyncio.run(main(parser.parse_args()))
