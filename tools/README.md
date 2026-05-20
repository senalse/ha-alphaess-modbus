# tools/

Developer tools for the AlphaESS Modbus integration. Run from the repo root.

**IMPORTANT:** The AlphaESS inverter allows only one TCP connection at a time.
Disable the HA integration before running these tools.

---

## scan_registers.py

Scans all known Modbus address ranges on the inverter and writes a CSV report.
Register labels are sourced at runtime from `custom_components/alphaess_modbus/const.py`,
so the output stays in sync with the integration without any manual upkeep.

```
python tools/scan_registers.py --host 192.168.1.100
python tools/scan_registers.py --host 192.168.1.100 --slave 85 --chunk 8
```

Output: `scan_results.csv` in the current directory.

---

## test_connection.py

Runs three quick Modbus read tests (connect, battery registers, wrong slave ID)
to verify the inverter is reachable and responding correctly.

```
python tools/test_connection.py --host 192.168.1.100
python tools/test_connection.py --host 192.168.1.100 --port 502 --slave 85
```
