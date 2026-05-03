# AlphaESS Modbus TCP — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/senalse/ha-alphaess-modbus.svg)](https://github.com/senalse/ha-alphaess-modbus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local Home Assistant integration for **AlphaESS solar inverters** (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via **Modbus TCP**.

No cloud account required. All communication is direct to the inverter on your local network.

Based on the excellent YAML package by [Axel Koegler](https://projects.hillviewlodge.ie/alphaess/).

---

## Features

- **94 sensor entities enabled by default** (159 total) — real-time power flows, battery SoC/SoH, cell voltages, temperatures, voltages, energy totals, dispatch diagnostics, grid safety parameters, faults & warnings
- **Force Charging** — charge battery from grid at configurable power (kW), duration, and cutoff SoC
- **Force Discharging** — discharge battery at configurable power, duration, and cutoff SoC; automatically stops 1% above the cutoff and resets dispatch so the inverter returns to self-consumption without any grid draw
- **Force Export** — export battery to grid at configurable power, duration, and cutoff SoC; same zero-grid-draw auto-stop as Force Discharging
- **Force Import** — import from grid at a configurable target kW, dynamically adjusting battery charge to offset live PV so total grid draw stays at the target; stops at cutoff SoC
- **Excess Export** — prioritise grid export over battery charging to reduce PV clipping
- **Smart Export** — dynamically exports up to a configurable max power, accounting for live house load and PV so grid export stays at the target without overloading the inverter
- **Battery cell health** — min/max cell voltages polled every 60 s; charge/discharge cutoff voltages, module count, capacity, and type available as diagnostic sensors
- **Dispatch diagnostics** — energy flow direction (human-readable), PV switch state, frequency dispatch flag, power, and frequency
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

Each sensor has a fixed poll interval hardcoded in the integration. The coordinator runs a 2-second master loop; contiguous registers due in the same cycle are batched into a single Modbus read. Individual registers are skipped when their own `scan_interval` hasn't elapsed yet.

| Interval | Sensors |
|----------|---------|
| **1 s** | Grid Power, Battery Power, Active Power PV Meter, PV String 1–4 Power, PV Total Power *(disabled by default)* |
| **5 s** | Grid Power Phase A/B/C, Grid Voltage Phase A/B/C, Inverter Work Mode, Inverter Power L1/L2/L3 + total, System Fault, Inverter Warning 1/2, Inverter Fault 1/2, Battery Warning/Fault, Max Feed to Grid, Dispatch registers (including Dispatch Energy Flow Direction, Freq Dispatch Flag), dispatch PV switch, freq dispatch power/frequency *(last two disabled by default)* |
| **10 s** | Battery SoC, Battery SoH, Battery min/max cell temps, Battery max charge/discharge current, Charging Time Period Control, Charging Cutoff SoC |
| **30 s** | Grid Frequency, Charging/Discharging period start/stop times, Discharging Cutoff SoC |
| **60 s** | Inverter Temperature, Battery Voltage/Current/Status/Remaining Time, Battery min/max cell voltages, Battery relay status *(disabled)*, PV String Voltage & Current, Energy Totals, Version strings, SOC Calibration Enable *(disabled)*, Network settings *(disabled)* |
| **300 s** | Battery charge/discharge cutoff voltages, Battery module count, Battery capacity, Battery type, SOC calibration cycle days *(all disabled by default)* |

There is no user-configurable poll interval — intervals are tuned per-sensor to balance responsiveness against the inverter's one-connection limit.

---

## Entities

### Sensors (read-only)

94 sensors are enabled by default; the remaining 65 are disabled and can be turned on individually in HA under Settings → Devices & Services → [device] → entities. Sensors marked *(disabled)* below are off by default.

#### Power (real-time)

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Grid Power | W | 1 s | Positive = import from grid, negative = export to grid |
| Battery Power | W | 1 s | Power to/from battery |
| Active Power PV Meter | W | 1 s | PV generation measured at the meter point |
| PV String 1 Power | W | 1 s | |
| PV String 2 Power | W | 1 s | |
| PV String 3 Power | W | 1 s | |
| PV String 4 Power | W | 1 s | |
| PV Total Power (Inverter) *(disabled)* | W | 1 s | Sum of all PV strings per inverter register 0x0453 |
| Current PV Production | W | calculated | Sum of all PV string powers + PV meter |
| Current House Load | W | calculated | Net house consumption derived from grid, battery, and PV |

#### Grid

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Grid Frequency | Hz | 30 s | |
| Grid Power Phase A | W | 5 s | |
| Grid Power Phase B | W | 5 s | |
| Grid Power Phase C | W | 5 s | |
| Grid Voltage Phase A | V | 5 s | |
| Grid Voltage Phase B | V | 5 s | |
| Grid Voltage Phase C | V | 5 s | |
| Max Feed to Grid | % | 5 s | Grid export limit as % of installed PV capacity |

#### Inverter

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Inverter Work Mode | - | 5 s | Operating mode code |
| Inverter Power L1 | W | 5 s | |
| Inverter Power L2 | W | 5 s | |
| Inverter Power L3 | W | 5 s | |
| Inverter Power | W | 5 s | Total AC output |
| Inverter Temperature | °C | 60 s | |
| Backup Inverter Power L1 *(disabled)* | W | 5 s | Backup output per phase |
| Backup Inverter Power L2 *(disabled)* | W | 5 s | |
| Backup Inverter Power L3 *(disabled)* | W | 5 s | |
| Backup Inverter Power *(disabled)* | W | 5 s | Total backup output |

#### PV Strings

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| PV String 1 Voltage | V | 60 s | |
| PV String 1 Current | A | 60 s | |
| PV String 2 Voltage | V | 60 s | |
| PV String 2 Current | A | 60 s | |
| PV String 3 Voltage | V | 60 s | |
| PV String 3 Current | A | 60 s | |
| PV String 4 Voltage | V | 60 s | |
| PV String 4 Current | A | 60 s | |
| PV Capacity Storage *(disabled)* | W | 60 s | Battery storage PV nameplate capacity |
| PV Capacity of Grid Inverter *(disabled)* | W | 60 s | Grid inverter PV nameplate capacity |
| CT Rate PV Meter *(disabled)* | - | 60 s | CT ratio for PV meter |
| CT Rate Grid Meter *(disabled)* | - | 60 s | CT ratio for grid meter |

#### Battery

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Battery State of Charge | % | 10 s | |
| Battery State of Health | % | 10 s | |
| Battery Min Cell Temp | °C | 10 s | Lowest cell temperature in pack |
| Battery Max Cell Temp | °C | 10 s | Highest cell temperature in pack |
| Battery Max Charge Current | A | 10 s | BMS-reported maximum |
| Battery Max Discharge Current | A | 10 s | BMS-reported maximum |
| Battery Voltage | V | 60 s | Pack terminal voltage |
| Battery Current | A | 60 s | Pack current |
| Battery Status | - | 60 s | BMS status code |
| Battery Remaining Time | min | 60 s | |
| Battery Min Cell Voltage | V | 60 s | Lowest cell voltage in pack (3 d.p.) |
| Battery Max Cell Voltage | V | 60 s | Highest cell voltage in pack (3 d.p.) |
| Battery Relay Status *(disabled)* | - | 60 s | BMS relay state |
| Battery Charge Cutoff Voltage *(disabled)* | V | 5 min | Hardware upper voltage limit from BMS |
| Battery Discharge Cutoff Voltage *(disabled)* | V | 5 min | Hardware lower voltage limit from BMS |
| Battery Module Count *(disabled)* | - | 5 min | Number of battery modules installed |
| Battery Capacity *(disabled)* | kWh | 5 min | Pack nameplate capacity |
| Battery Type *(disabled)* | - | 5 min | Battery type code from BMS |

#### Energy Totals (lifetime)

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Total Energy from PV | kWh | 60 s | Lifetime PV generation |
| Total Energy Feed to Grid (Meter) | kWh | 60 s | Lifetime export measured at grid meter |
| Total Energy Consumption from Grid (Meter) | kWh | 60 s | Lifetime import measured at grid meter |
| Total Energy Feed to Grid (PV) | kWh | 60 s | Lifetime export measured at PV meter |
| Total Energy Charge Battery | kWh | 60 s | Lifetime energy delivered into battery |
| Total Energy Discharge Battery | kWh | 60 s | Lifetime energy drawn from battery |
| Total Energy Charge Battery from Grid | kWh | 60 s | Lifetime grid-to-battery energy |

#### Faults & Warnings

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| System Fault | - | 5 s | Active fault code (0 = no fault) |
| Inverter Warning 1 | - | 5 s | Inverter warning bitmask |
| Inverter Warning 2 | - | 5 s | |
| Inverter Fault 1 | - | 5 s | Inverter fault bitmask |
| Inverter Fault 2 | - | 5 s | |
| Battery Warning | - | 5 s | BMS-level battery warning |
| Battery Fault | - | 5 s | BMS-level battery fault |
| Battery 1 Warning *(disabled)* | - | 5 s | Per-module warning, modules 1–6 |
| Battery 2 Warning *(disabled)* | - | 5 s | |
| Battery 3 Warning *(disabled)* | - | 5 s | |
| Battery 4 Warning *(disabled)* | - | 5 s | |
| Battery 5 Warning *(disabled)* | - | 5 s | |
| Battery 6 Warning *(disabled)* | - | 5 s | |
| Battery 1 Fault *(disabled)* | - | 5 s | Per-module fault, modules 1–6 |
| Battery 2 Fault *(disabled)* | - | 5 s | |
| Battery 3 Fault *(disabled)* | - | 5 s | |
| Battery 4 Fault *(disabled)* | - | 5 s | |
| Battery 5 Fault *(disabled)* | - | 5 s | |
| Battery 6 Fault *(disabled)* | - | 5 s | |

#### Dispatch & Diagnostics

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Dispatch Start | - | 5 s | 1 = dispatch active, 0 = stopped |
| Dispatch Active Power | W | 5 s | Current dispatch power (offset-decoded; negative = charge) |
| Dispatch Reactive Power | W | 5 s | |
| Dispatch Mode | - | 5 s | Current dispatch mode code |
| Dispatch SoC | % | 5 s | Current SoC target |
| Dispatch Time | s | 5 s | Remaining dispatch duration |
| Dispatch Energy Flow Direction | - | 5 s | Human-readable flow direction: PV to Grid, Battery to Grid, Grid to Battery, etc. |
| Freq Dispatch Flag | - | 5 s | 0 = Normal, 1 = frequency dispatch active |
| Dispatch PV Switch *(disabled)* | - | 5 s | PV switch state during dispatch |
| Freq Dispatch Power *(disabled)* | W | 5 s | Frequency dispatch power setpoint |
| Freq Dispatch Frequency *(disabled)* | Hz | 5 s | Frequency dispatch trigger frequency |

#### Scheduling — Charging / Discharging Periods

These are read-only sensor views of the scheduling registers. The writable equivalents are the Time and Number entities listed under Controls below.

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Charging Time Period Control | - | 10 s | Mode code: 0 = Disable, 1 = Grid Charging, 2 = Discharge Time Control, 3 = Both |
| Charging Cutoff SoC | % | 10 s | Stop charging at this SoC |
| Charging Period 1 Start Hour | h | 30 s | |
| Charging Period 1 Stop Hour | h | 30 s | |
| Charging Period 2 Start Hour | h | 30 s | |
| Charging Period 2 Stop Hour | h | 30 s | |
| Charging Period 1 Start Minute | min | 30 s | |
| Charging Period 1 Stop Minute | min | 30 s | |
| Charging Period 2 Start Minute | min | 30 s | |
| Charging Period 2 Stop Minute | min | 30 s | |
| Discharging Cutoff SoC | % | 30 s | Stop discharging at this SoC |
| Discharging Period 1 Start Hour | h | 30 s | |
| Discharging Period 1 Stop Hour | h | 30 s | |
| Discharging Period 2 Start Hour | h | 30 s | |
| Discharging Period 2 Stop Hour | h | 30 s | |
| Discharging Period 1 Start Minute | min | 30 s | |
| Discharging Period 1 Stop Minute | min | 30 s | |
| Discharging Period 2 Start Minute | min | 30 s | |
| Discharging Period 2 Stop Minute | min | 30 s | |

#### Inverter & System Info

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Inverter Serial Number | - | 60 s | |
| Inverter Version | - | 60 s | DSP firmware version string |
| Inverter ARM Version | - | 60 s | ARM firmware version string |
| BMS Version | - | 60 s | |
| LMU Version | - | 60 s | |
| ISO Version | - | 60 s | |
| EMS Version High | - | 60 s | |
| EMS Version Middle | - | 60 s | |
| EMS Version Low | - | 60 s | |
| EMS Version Low Suffix | - | 60 s | |
| System Time YYMM *(disabled)* | - | 5 s | Raw year/month packed register |
| System Time DDHH *(disabled)* | - | 5 s | Raw day/hour packed register |
| System Time MMSS *(disabled)* | - | 5 s | Raw minute/second packed register |

#### Network (all disabled by default)

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Modbus Baud Rate *(disabled)* | - | 60 s | |
| IP Method *(disabled)* | - | 60 s | 0 = DHCP, 1 = Static |
| Local IP (raw) *(disabled)* | - | 60 s | 32-bit packed IP address |
| Subnet Mask (raw) *(disabled)* | - | 60 s | 32-bit packed subnet mask |
| Gateway (raw) *(disabled)* | - | 60 s | 32-bit packed gateway address |

#### Grid Safety (all disabled by default)

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Grid Regulation *(disabled)* | - | 60 s | Grid standard code |
| Overvoltage Protection L1 *(disabled)* | V | 60 s | |
| Overvoltage Protection L1 Time *(disabled)* | ms | 60 s | |
| Overvoltage Protection L2 *(disabled)* | V | 60 s | |
| Overvoltage Protection L2 Time *(disabled)* | ms | 60 s | |
| Overvoltage Protection L3 *(disabled)* | V | 60 s | |
| Overvoltage Protection L3 Time *(disabled)* | ms | 60 s | |
| Overvoltage Protection 10min *(disabled)* | V | 60 s | 10-minute average overvoltage threshold |
| Overvoltage Protection 10min Time *(disabled)* | s | 60 s | |
| Undervoltage Protection L1 *(disabled)* | V | 60 s | |
| Undervoltage Protection L1 Time *(disabled)* | ms | 60 s | |
| Undervoltage Protection L2 *(disabled)* | V | 60 s | |
| Undervoltage Protection L2 Time *(disabled)* | ms | 60 s | |
| Undervoltage Protection L3 *(disabled)* | V | 60 s | |
| Undervoltage Protection L3 Time *(disabled)* | ms | 60 s | |
| Overfrequency Protection L1 *(disabled)* | Hz | 60 s | |
| Overfrequency Protection L1 Time *(disabled)* | ms | 60 s | |
| Overfrequency Protection L2 *(disabled)* | Hz | 60 s | |
| Overfrequency Protection L2 Time *(disabled)* | ms | 60 s | |
| Overfrequency Protection L3 *(disabled)* | Hz | 60 s | |
| Overfrequency Protection L3 Time *(disabled)* | ms | 60 s | |
| Underfrequency Protection L1 *(disabled)* | Hz | 60 s | |
| Underfrequency Protection L1 Time *(disabled)* | ms | 60 s | |
| Underfrequency Protection L2 *(disabled)* | Hz | 60 s | |
| Underfrequency Protection L2 Time *(disabled)* | ms | 60 s | |
| Underfrequency Protection L3 *(disabled)* | Hz | 60 s | |
| Underfrequency Protection L3 Time *(disabled)* | ms | 60 s | |

### Controls

| Entity | Type | Description |
|--------|------|-------------|
| Force Charging | Switch | Charge battery from grid at configured power/duration/cutoff SoC |
| Force Discharging | Switch | Discharge battery at configured power/duration/cutoff SoC; auto-stops ~1% above cutoff to guarantee no grid draw during transition |
| Force Export | Switch | Export to grid at configured power/duration/cutoff SoC; same zero-grid-draw auto-stop as Force Discharging |
| Force Import | Switch | Import from grid at a target kW, dynamically adjusted for live PV so total grid draw stays at the target; stops at cutoff SoC |
| Force Import Pause | Switch | Temporarily pause Force Import without losing its active state |
| Dispatch | Switch | Generic dispatch — mode, power, SoC target, and duration all configurable independently |
| Excess Export | Switch | Maximise PV export, reduce clipping (re-fires every 4 min) |
| Excess Export Pause | Switch | Temporarily pause Excess Export without losing its active state |
| Smart Export | Switch | Dynamically exports up to Max Export Power, adjusted for live house load and PV (re-fires every 30 s) |
| Force Charging Power | Number | Charging power in kW (0–20) |
| Force Charging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Charging Cutoff SoC | Number | Stop charging at this SoC % |
| Force Discharging Power | Number | Discharging power in kW (0–20) |
| Force Discharging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Discharging Cutoff SoC | Number | Stop discharging at this SoC % (switch auto-stops ~1% above this) |
| Force Export Power | Number | Export power in kW (0–20) |
| Force Export Duration | Number | Duration in minutes (0–480, step 5) |
| Force Export Cutoff SoC | Number | Stop exporting at this SoC % (switch auto-stops ~1% above this) |
| Force Import Power | Number | Target grid import in kW (0–20) |
| Force Import Duration | Number | Duration in minutes (0–480, step 5) |
| Force Import Cutoff SoC | Number | Stop importing at this SoC % |
| Dispatch Power | Number | Dispatch power in kW (−20 to +20; negative = charge, positive = discharge/export) |
| Dispatch Duration | Number | Duration in minutes (0–480, step 5) |
| Dispatch Cutoff SoC | Number | SoC target % for the generic Dispatch switch |
| Max Export Power | Number | Target grid export for Smart Export (kW) |
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
| Restart PCS | Button | Restart the Power Conversion System |
| Restart EMS | Button | Restart the Energy Management System |
| Reset Energy Totals | Button | **WARNING: clears all lifetime energy counters on the inverter.** Use only if you have intentionally replaced the inverter or need to zero out the totals. |

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

| File | Description | Custom cards required |
|------|-------------|----------------------|
| `alphaess_dashboard_pfcp.yaml` | Sections-layout dashboard with live power flow diagram — battery controls, scheduling, dispatch, energy stats, system info | [power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus) |
| `alphaess_dashboard.yaml` | Sections-layout dashboard without custom cards — gauge + glance live view, battery controls, scheduling, dispatch, energy stats, system info | None |
| `power_diagram.yaml` | Power flow chart for today | [ApexCharts Card](https://github.com/RomRider/apexcharts-card) |
| `power_diagram_extended.yaml` | Extended power diagrams — today, yesterday, 3-day, string detail, instant, and hi-res views | [ApexCharts Card](https://github.com/RomRider/apexcharts-card) |

### How to use

1. Install any required custom cards via HACS (see table above):
   - **power-flow-card-plus**: HACS → Frontend → search "Power Flow Card Plus" → Download
   - **ApexCharts Card**: HACS → Frontend → search "ApexCharts Card" → Download
2. In Home Assistant go to **Settings → Dashboards → Add Dashboard**
3. Switch to YAML mode and paste the contents of the example file

   Or use the **Raw configuration editor** on an existing dashboard to add the views — paste the content starting from the `views:` key.

4. Reload the dashboard browser tab after installing any custom cards

> **EV Charger entity:** `alphaess_dashboard_pfcp.yaml` includes `sensor.charger_power_active_import` in the power flow diagram. If you do not have an EV charger, remove the `individual:` block from the `custom:power-flow-card-plus` card.

> All entity IDs follow the pattern `sensor.alphaess_inverter_*`, `switch.alphaess_inverter_*`, etc. (the device name is "AlphaESS Inverter", which Home Assistant uses as the entity ID prefix).

---

## Changelog

### v1.9.2
- **fix:** dev tools (`scan_registers.py`, `test_connection.py`) moved from the repo root to `tools/` so HACS does not surface them alongside the integration. `scan_registers.py` now builds its register label map from `SENSOR_REGISTERS` at runtime instead of a static dict, keeping it in sync automatically. `test_connection.py` now accepts `--host`, `--port`, and `--slave` arguments instead of hardcoded constants. A `tools/README.md` with usage examples is included.

### v1.9.1
- **fix:** removed unused `DEFAULT_SCAN_INTERVAL` and `MODBUS_HUB` constants from `const.py` (neither was imported anywhere).
- **fix:** `time.py` `async_set_value` now captures the current hour value before writing and rolls it back if the subsequent minute write raises an exception, so the inverter's schedule registers are never left in a half-updated state. A warning is logged when rollback fires.

### v1.9.0
- **feat:** reconnect storm protection - `modbus_client` now tracks consecutive connection failures and enforces a 10-second backoff after 3 in a row, so a TCP disconnect no longer fires dozens of blocking retry loops within one coordinator cycle. `connect()` is also guarded by a lock so concurrent callers coalesce into a single attempt.
- **feat:** coordinator aborts a cycle early (raising `UpdateFailed`) after more than 5 read errors, letting HA's built-in backoff handle the retry rather than grinding through all remaining registers on a dead connection.
- **feat:** number, select, and switch entities now expose an `available` property tied to `coordinator.last_update_success`, so all controls go unavailable during an outage instead of showing stale data (sensor entities already had this via `CoordinatorEntity`).

### v1.8.1
- **fix:** `coordinator.data` entries are now expired after 5x their `scan_interval` has elapsed without a successful read. Registers that start failing permanently (e.g. firmware change) will report `unknown` rather than keeping a stale value indefinitely.
- **fix:** removed `async_request_refresh()` from `async_write_dispatch`, `async_write_register`, and `async_write_registers`. These helpers were queuing a full coordinator poll after every write, causing extra round-trips and contention during active dispatch sequences. The 2-second poll loop delivers readback fast enough; `async_sync_datetime` retains its refresh so the UI updates immediately after a clock sync.
- **fix:** `async_sync_datetime` now writes all three time registers (0x0740-0x0742) in a single `write_registers` call instead of three sequential writes with 100 ms sleeps between them, eliminating the window where the inverter clock is only partially updated. BCD encoding (confirmed correct on this inverter) is unchanged.

### v1.8.0
- **feat:** batch contiguous Modbus register reads — adjacent registers (gap <= 4) are merged into a single `read_holding_registers` call per cycle, reducing typical transaction count from ~50 to ~10 per poll. Coordinator poll interval bumped from 1 s to 2 s; per-sensor `scan_interval` cadence is unchanged.
- **feat:** SOC watcher samples battery SoC every 2 s (down from 10 s) while a force-discharge, force-export, or SOC-watcher switch is active, tightening the cutoff margin for the zero-grid-draw invariant.
- **feat:** number and select sliders now source their displayed value from live coordinator data (the actual inverter register) rather than the last HA-saved state after a restart — so the UI immediately reflects changes made via the AlphaESS app or another client.
- **fix:** switch.py no longer looks up number/select values by hardcoded `hass.states.get("number.alphaess_inverter_*")` entity ID slugs. Values are now read from `coordinator.numbers` / `coordinator.selects`, which are seeded by the entities themselves on startup and kept current on every write. Dispatch mode and parameter sliders work correctly even if the device is renamed in HA.

### v1.7.4
- **fix:** 15 dispatch-parameter `ModbusNumberDef` entries (force-charging/discharging/export/import cutoff SoC, duration, and power; dispatch cutoff SoC, duration, and power) now have `address=None`. Previously they carried misleading register addresses that were never written directly, but could have caused silent state corruption if called via `async_write_register`.

### v1.7.3
- **fix:** track async tasks with `hass.async_create_task` so a reload mid-dispatch no longer leaks coroutines or logs "Task was destroyed but it is pending" errors
- **fix:** raise `ConfigEntryNotReady` on connection failure so HA retries automatically instead of marking the entry permanently failed
- **feat:** add hassfest and HACS validation CI (`.github/workflows/validate.yml`)

### v1.7.2
- **fix:** remove SOC calibration scheduling entities (SOC Calibration switch, SOC Calibration Enable switch, SOC Calibration Cycle Mode select, SOC Calibration Cycle Days number) - registers 0x1900-0x1903 return Illegal Data Address on current inverter firmware; the read-only Battery SOC Calibration status sensor at 0x012F remains. Use a Home Assistant automation to trigger a calibration cycle via the AlphaESS app or inverter web UI instead.

### v1.7.1
- **fix:** single-register writes (selects, numbers, buttons, time entities) were using Modbus FC16 (Write Multiple Registers) instead of FC6 (Write Single Register). Many AlphaESS inverters reject FC16 for individual registers with exception code 2 (Illegal Data Address). All single-register writes now correctly use FC6. Dispatch block writes (9 registers at 0x0880) remain on FC16.

### v1.7.0
- **feat:** 18 new entities - battery health (SoH, cell voltages, cell temps, relay status, module count, capacity), dispatch diagnostics (energy flow direction, freq dispatch flag and power/frequency setpoints), and SOC calibration scheduling (enable switch, trigger switch, cycle mode select, cycle days number)

### v1.6.5
- **feat:** Force Charging Hold and Force Import Hold switches - hold the inverter in force-charge or force-import mode indefinitely without a dispatch timeout

### v1.6.4
- **fix:** force discharge and force export now stop 1% above the SOC cutoff to guarantee zero grid draw on the GloBird ZeroHero plan (previously the inverter could briefly draw from grid as SoC hit the limit)

### v1.6.3
- **fix:** add SOC watcher to stop force discharging/export immediately when cutoff SoC is reached

### v1.6.2
- **fix:** use 60 s refresh loop for force discharging/export to guarantee dispatch reset on SOC cutoff

### v1.6.1
- **fix:** stop force discharge/charge/export immediately when SOC cutoff is reached

### v1.6.0
- **feat:** add Force Import switch, replace Smart Charge

---

## Credits

This integration is based on the YAML package developed by **Axel Koegler** and documented at [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/). All Modbus register mappings are derived from that work and the AlphaESS Modbus register documentation.

---

## License

MIT — see [LICENSE](LICENSE)
