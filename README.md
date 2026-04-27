# AlphaESS Modbus TCP — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/senalse/ha-alphaess-modbus.svg)](https://github.com/senalse/ha-alphaess-modbus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local Home Assistant integration for **AlphaESS solar inverters** (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via **Modbus TCP**.

No cloud account required. All communication is direct to the inverter on your local network.

Based on the excellent YAML package by [Axel Koegler](https://projects.hillviewlodge.ie/alphaess/).

---

## Features

- **90 sensor entities enabled by default** (145 total) — real-time power flows, battery SoC/SoH, temperatures, voltages, energy totals, grid safety parameters, faults & warnings
- **Force Charging** — charge battery from grid at configurable power (kW), duration, and cutoff SoC
- **Force Discharging** — discharge battery at configurable power and duration
- **Force Export** — export to grid at configurable power
- **Excess Export** — prioritise grid export over battery charging to reduce PV clipping
- **Smart Export** — dynamically exports up to a configurable max power, accounting for live house load and PV so grid export stays at the target without overloading the inverter
- **Smart Charge** — dynamically charges from grid up to a configurable max power, offset by live PV production so you only import what PV can't cover
- **Charging / Discharging time periods** — configure up to two charge and discharge windows
- **Dispatch mode selector** — Battery only, SoC Control, Load Following, Maximise Output, and more
- **Max Feed to Grid** — set grid export limit as % of installed PV capacity
- **Date & Time sync** — sync inverter clock to Home Assistant system time
- **Sync Dispatch State** — reconcile HA switch states with the inverter after a restart

---

## Requirements

- AlphaESS inverter with **Modbus TCP enabled** on port 502
- Inverter reachable on your local network (wired LAN or powerline recommended)
- Home Assistant **2024.10 or newer**
- HACS installed

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom Repositories**
3. Add `https://github.com/senalse/ha-alphaess-modbus` — category: **Integration**
4. Click **Download** on the AlphaESS Modbus TCP card
5. Restart Home Assistant

### Manual

1. Download the latest release from the [Releases page](https://github.com/senalse/ha-alphaess-modbus/releases)
2. Copy the `custom_components/alphaess_modbus` folder into your HA config directory under `custom_components/`
3. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **AlphaESS Modbus TCP**
3. Fill in the details:

| Field | Default | Notes |
|-------|---------|-------|
| Inverter IP Address | — | Use a DHCP reservation for a stable address |
| Modbus Port | `502` | Change only if you've modified the inverter setting |
| Slave ID | `85` | Standard for AlphaESS inverters |

4. Click **Submit** — Home Assistant will test the connection before saving

---

## Poll Intervals

Each sensor has a fixed poll interval hardcoded in the integration. The coordinator runs a 1-second master loop and skips registers that aren't due yet.

| Interval | Sensors |
|----------|---------|
| **1 s** | Grid Power, Battery Power, Active Power PV Meter, PV String 1–4 Power |
| **5 s** | Grid Power Phase A/B/C, Grid Voltage Phase A/B/C, Inverter Work Mode, Inverter Power L1/L2/L3 + total, System Fault, Inverter Warning 1/2, Inverter Fault 1/2, Battery Warning/Fault, Max Feed to Grid, Dispatch registers |
| **10 s** | Battery SoC, Battery SoH, Battery min/max cell temps, Battery max charge/discharge current, Charging Time Period Control, Charging Cutoff SoC |
| **30 s** | Grid Frequency, Charging/Discharging period start/stop times, Discharging Cutoff SoC |
| **60 s** | Inverter Temperature, Battery Voltage/Current/Status/Remaining Time, PV String Voltage & Current, Energy Totals, Version strings, Network settings *(disabled by default)* |

There is no user-configurable poll interval — intervals are tuned per-sensor to balance responsiveness against the inverter's one-connection limit.

---

## Entities

### Sensors (read-only)

| Entity | Description |
|--------|-------------|
| Battery State of Charge | Battery % (SoC) |
| Battery State of Health | Battery health % (SoH) |
| Grid Power | Power to/from grid (W, negative = export) |
| Battery Power | Power to/from battery (W) |
| PV String 1–4 Power | Power from each PV string (W) |
| Current PV Production | Calculated — sum of all PV strings + PV meter (W) |
| Current House Load | Calculated — net house consumption derived from grid, battery, and PV (W) |
| Inverter Temperature | Inverter temperature (°C) |
| Total Energy from PV | Lifetime PV generation (kWh) |
| Total Energy Feed to Grid | Lifetime grid export (kWh) |
| System Fault | Active fault code (0 = no fault) |
| … and 80+ more | See the Devices page in HA for the full list |

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| Force Charging | Switch | Charge battery from grid at configured power/duration/cutoff SoC |
| Force Discharging | Switch | Discharge battery at configured power/duration/cutoff SoC |
| Force Export | Switch | Export to grid at configured power/duration/cutoff SoC |
| Dispatch | Switch | Generic dispatch — mode, power, SoC target, and duration all configurable independently |
| Excess Export | Switch | Maximise PV export, reduce clipping (re-fires every 4 min) |
| Excess Export Pause | Switch | Temporarily pause Excess Export without losing its active state |
| Smart Export | Switch | Dynamically exports up to Max Export Power, adjusted for live house load and PV (re-fires every 30 s) |
| Smart Charge | Switch | Dynamically charges up to Max Import Power from grid, offset by live PV production (re-fires every 30 s) |
| Force Charging Power | Number | Charging power in kW (0–20) |
| Force Charging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Charging Cutoff SoC | Number | Stop charging at this SoC % |
| Force Discharging Power | Number | Discharging power in kW (0–20) |
| Force Discharging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Discharging Cutoff SoC | Number | Stop discharging at this SoC % |
| Force Export Power | Number | Export power in kW (0–20) |
| Force Export Duration | Number | Duration in minutes (0–480, step 5) |
| Force Export Cutoff SoC | Number | Stop exporting at this SoC % |
| Dispatch Power | Number | Dispatch power in kW (−20 to +20; negative = charge, positive = discharge/export) |
| Dispatch Duration | Number | Duration in minutes (0–480, step 5) |
| Dispatch Cutoff SoC | Number | SoC target % for the generic Dispatch switch |
| Max Export Power | Number | Target grid export for Smart Export (kW) |
| Max Import Power | Number | Target grid import for Smart Charge (kW) |
| Dispatch Mode | Select | Operating mode for the generic Dispatch switch (Battery Only, SoC Control, Load Following, etc.) |
| Charging / Discharging Settings | Select | Enable/disable time period control (Disable / Grid Charging / Discharge Time Control / Both) |
| Inverter AC Limit | Select | Inverter AC output capacity (3–20 kW) — used by Excess Export and Smart Export to avoid overloading the inverter |
| Max Feed to Grid | Number | Grid export limit (% of PV capacity) |
| Charging Period 1 Start Time | Time | hh:mm — writes hour and minute registers independently |
| Charging Period 1 Stop Time | Time | hh:mm |
| Charging Period 2 Start Time | Time | hh:mm |
| Charging Period 2 Stop Time | Time | hh:mm |
| Discharging Period 1 Start Time | Time | hh:mm |
| Discharging Period 1 Stop Time | Time | hh:mm |
| Discharging Period 2 Start Time | Time | hh:mm |
| Discharging Period 2 Stop Time | Time | hh:mm |
| Dispatch Reset | Button | Reset all dispatch registers immediately |
| Synchronise Date & Time | Button | Sync inverter clock to HA system time |
| Sync Dispatch State | Button | Reconcile HA switch states with the inverter (use after HA restart if dispatch was running) |

---

## Network Setup

For reliable Modbus TCP connectivity:

1. Connect the inverter's **LAN port** directly to your router (or via a switch)
2. Set a **DHCP reservation** in your router so the inverter always gets the same IP
3. If your inverter is on Wi-Fi, a **powerline adapter** or **Wi-Fi repeater in bridge mode** works well

The inverter's Modbus TCP port is `502` and the slave ID is `85` by default. These can be verified in the AlphaESS app under **Settings → Communication**.

---

## Troubleshooting

**Integration won't connect**
- Confirm the inverter IP is reachable: try `ping <inverter-ip>` from your HA host
- Check that Modbus TCP is enabled on the inverter (AlphaESS app → Settings → Communication)
- Make sure no firewall is blocking port 502
- AlphaESS inverters only allow **one Modbus TCP connection at a time** — if another app (a second HA instance, a Modbus tool, Alpha2MQTT, etc.) is already connected, HA will be refused. Disconnect the other client and reload the integration

**Entities show unavailable after some time**
- This can happen if the inverter goes into sleep/standby mode at night — it recovers automatically when the inverter wakes up
- Check HA logs for Modbus timeout errors

**Force charging / dispatch not working**
- Only one dispatch mode can be active at a time — activating one switch will deactivate any other active switch
- Dispatch automatically resets after the configured duration expires

---

## Dashboards

Example Lovelace dashboard configurations are included in the [`examples/`](examples/) folder:

| File | Description |
|------|-------------|
| `alphaess_view.yaml` | Full control dashboard — charging, dispatch, battery, grid, energy stats, system info |
| `power_diagram.yaml` | Power flow chart for today (requires [ApexCharts Card](https://github.com/RomRider/apexcharts-card)) |
| `power_diagram_extended.yaml` | Extended power diagrams — today, yesterday, 3-day, instant, and hi-res views |

### How to use

1. Install the **[ApexCharts Card](https://github.com/RomRider/apexcharts-card)** from HACS (required for power diagrams)
2. In Home Assistant go to **Settings → Dashboards → Add Dashboard**
3. Switch to YAML mode and paste the contents of the example file, or use the **Raw configuration editor** to add the views to an existing dashboard

> The dashboard files reference entity IDs created by this integration. All entity IDs follow the pattern `sensor.alphaess_inverter_*`, `switch.alphaess_inverter_*`, etc. (the device name is "AlphaESS Inverter", which Home Assistant uses as the entity ID prefix).

---

## Credits

This integration is based on the YAML package developed by **Axel Koegler** and documented at [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/). All Modbus register mappings are derived from that work and the AlphaESS Modbus register documentation.

---

## License

MIT — see [LICENSE](LICENSE)
