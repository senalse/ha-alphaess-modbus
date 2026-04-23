# AlphaESS Modbus TCP — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/senalse/ha-alphaess-modbus.svg)](https://github.com/senalse/ha-alphaess-modbus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local Home Assistant integration for **AlphaESS solar inverters** (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via **Modbus TCP**.

No cloud account required. All communication is direct to the inverter on your local network.

Based on the excellent YAML package by [Axel Koegler](https://projects.hillviewlodge.ie/alphaess/).

---

## Features

- **90+ sensor entities enabled by default** (143 total) — real-time power flows, battery SoC/SoH, temperatures, voltages, energy totals, grid safety parameters, faults & warnings
- **Force Charging** — charge battery from grid at configurable power (kW), duration, and cutoff SoC
- **Force Discharging** — discharge battery at configurable power and duration
- **Force Export** — export to grid at configurable power
- **Excess Export** — prioritise grid export over battery charging to reduce PV clipping
- **Charging / Discharging time periods** — configure up to two charge and discharge windows
- **Dispatch mode selector** — Battery only, SoC Control, Load Following, Maximise Output, and more
- **Max Feed to Grid** — set grid export limit as % of installed PV capacity
- **Date & Time sync** — sync inverter clock to Home Assistant system time

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
| Scan Interval | `30` | Seconds between polls (fast sensors override this) |

4. Click **Submit** — Home Assistant will test the connection before saving

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
| Current PV Production | Sum of all PV strings + PV meter (W) |
| Inverter Temperature | Inverter temperature (°C) |
| Total Energy from PV | Lifetime PV generation (kWh) |
| Total Energy Feed to Grid | Lifetime grid export (kWh) |
| System Fault | Active fault code (0 = no fault) |
| … and 50+ more | See the Devices page in HA for the full list |

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| Force Charging | Switch | Charge battery from grid |
| Force Discharging | Switch | Discharge battery |
| Force Export | Switch | Export to grid |
| Excess Export | Switch | Maximise PV export, reduce clipping |
| Force Charging Power | Number | Power in kW (0–20 kW) |
| Force Charging Duration | Number | Duration in minutes |
| Force Charging Cutoff SoC | Number | Stop charging at this SoC % |
| Dispatch Mode | Select | Operating mode for dispatch |
| Charging / Discharging Settings | Select | Enable/disable time period control |
| Max Feed to Grid | Number | Grid export limit (% of PV capacity) |
| Dispatch Reset | Button | Reset all dispatch registers |
| Synchronise Date & Time | Button | Sync inverter clock to HA time |

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

> The dashboard files reference entity IDs created by this integration. All entity IDs follow the pattern `sensor.alphaess_*`, `switch.alphaess_*`, etc.

---

## Credits

This integration is based on the YAML package developed by **Axel Koegler** and documented at [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/). All Modbus register mappings are derived from that work and the AlphaESS Modbus register documentation.

---

## License

MIT — see [LICENSE](LICENSE)
