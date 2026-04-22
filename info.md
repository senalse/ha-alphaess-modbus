# AlphaESS Modbus TCP

Local Home Assistant integration for AlphaESS solar inverters (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via Modbus TCP.

No cloud dependency. All communication is direct to the inverter on your LAN.

## Features

- **60+ sensor entities** — real-time power flows, battery SoC/SoH, temperatures, energy totals, grid safety parameters, faults & warnings
- **Force Charging** — charge battery from grid at configurable power and duration
- **Force Discharging** — discharge battery at configurable power and duration
- **Force Export** — export to grid at configurable power
- **Excess Export** — prioritise grid export over battery charging (reduces clipping)
- **Charging/Discharging time periods** — configure charge and discharge windows
- **Dispatch mode selector** — SoC Control, Load Following, Maximise Output, and more
- **Max Feed to Grid** — set grid export limit as % of PV capacity
- **Date/Time sync** — sync inverter clock to HA system time

## Requirements

- AlphaESS inverter with Modbus TCP enabled (port 502)
- Inverter reachable via LAN
- Home Assistant 2024.10 or newer

## Setup

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**
2. Search for **AlphaESS Modbus TCP**
3. Enter your inverter's IP address (use a DHCP reservation for a stable address)
4. Leave port as `502` and slave ID as `85` unless you changed these on the inverter
5. Click **Submit**

## Credits

Based on the YAML integration by Axel Koegler — [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/)
