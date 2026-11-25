# AlphaESS Modbus TCP

Local Home Assistant integration for AlphaESS solar inverters (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via Modbus TCP.

No cloud dependency. All communication is direct to the inverter on your LAN.

## Features

- **91 of 168 sensors enabled by default**, the rest available when you want them: real-time power flows, battery SoC/SoH, per-module temperatures and cell voltages, energy totals, grid safety parameters, faults and warnings
- **Controls**: 22 numbers, 13 switches, 8 time entities, 6 buttons, 3 selects and 3 status flags
- **Peak Shaving**: hold grid import at or below a limit you set by discharging the battery to cover the rest. For an EV charger or another large load Home Assistant cannot control, or a connection with a capacity limit. Optionally also charges with the headroom below the limit, so import stays flat and the battery buffers both ways
- **Force Charging**: charge the battery from the grid at a set power and duration
- **Force Discharging**: discharge the battery at a set power and duration
- **Force Export**: hold a set export at the grid meter, adjusting for house load and solar automatically
- **Force Import**: hold a set import at the grid meter, buffering the difference into the battery
- **Excess Export**: prioritise grid export over battery charging to reduce clipping
- **Hold switches**: keep a force mode running for its full duration instead of stopping when the battery goes idle
- **Dispatch**: direct control of the inverter's dispatch block, with a mode selector (SoC Control, Load Following, Maximise Output and more)
- **Charging and discharging time periods**: configure the inverter's own charge and discharge windows
- **Max Feed to Grid**: set the grid export limit as a percentage of PV capacity
- **SoC calibration scheduling**: enable calibration and set a one-shot or recurring cycle
- **Date and time sync**: set the inverter clock from Home Assistant
- Every control is mutually exclusive where the inverter requires it, comes back off after a restart rather than resuming unattended, and reverts the inverter to normal operation within five minutes if Home Assistant stops

## Requirements

- AlphaESS inverter with Modbus TCP enabled (port 502)
- Inverter reachable via LAN
- Home Assistant 2024.10 or newer

## Setup

1. In Home Assistant, go to **Settings > Devices & Services > Add Integration**
2. Search for **AlphaESS Modbus TCP**
3. Enter your inverter's IP address (use a DHCP reservation for a stable address)
4. Leave port as `502` and slave ID as `85` unless you changed these on the inverter
5. Click **Submit**

The host, port and slave ID can be changed later from the integration's Configure option, without removing and re-adding it.

## Credits

Based on the YAML integration by Axel Koegler: [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/)
