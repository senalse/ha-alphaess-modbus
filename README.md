# AlphaESS Modbus TCP - Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/senalse/ha-alphaess-modbus.svg)](https://github.com/senalse/ha-alphaess-modbus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Local Home Assistant integration for **AlphaESS solar inverters** (SMILE-M5, SMILE5, SMILE-G3, SMILE-Hi, SMILE-B3 series) via **Modbus TCP**.

No cloud account required. All communication is direct to the inverter on your local network.

Based on the excellent YAML package by [Axel Koegler](https://projects.hillviewlodge.ie/alphaess/).

> **Disclaimer**
> This is an unofficial community integration, not affiliated with or supported by AlphaESS.
> The integration can write values directly to your inverter's Modbus registers. Incorrect
> values -- wrong power levels, bad SoC limits, or invalid dispatch parameters -- can
> damage your battery or cause unexpected inverter behaviour. Use this integration at your
> own risk. The author accepts no responsibility for damage to hardware or loss of data.

---

## Features

- **111 sensor entities enabled by default** (188 total) - real-time power flows, battery SoC/SoH, cell voltages, temperatures, voltages, energy totals, daily energy summaries, dispatch diagnostics, grid safety parameters, faults & warnings
- **Force Charging** - charge battery from grid at configurable power (kW), duration, and cutoff SoC
- **Force Charging Hold** - keeps Force Charging running indefinitely after the duration expires; turn on before starting Force Charging for continuous charging without a time limit
- **Force Discharging** - discharge battery at configurable power, duration, and cutoff SoC; automatically stops 1% above the cutoff and resets dispatch so the inverter returns to self-consumption without any grid draw
- **Force Discharging Hold** - keeps Force Discharging running for the full configured duration instead of stopping early when the SoC target is reached
- **Force Export** - export to grid at a target feed-in rate (kW); battery discharge is dynamically adjusted for live house load and PV so the grid sees the configured power; stops automatically when the duration expires or battery reaches the cutoff SoC
- **Force Export Hold** - keeps Force Export running indefinitely after the duration expires; turn on before starting Force Export for continuous export without a time limit
- **Force Import** - import from grid at a configurable target kW, dynamically adjusting battery charge to offset live PV so total grid draw stays at the target; stops at cutoff SoC
- **Force Import Hold** - keeps Force Import running indefinitely after the duration expires; turn on before starting Force Import for continuous importing without a time limit
- **Excess Export** - charge the battery with PV power that would otherwise be clipped by the inverter AC output limit; automatically pauses when the house starts drawing from the grid and resumes once PV recovers
- **Dispatch PV Enabled** - enable or disable the inverter's PV coupling during an active dispatch (useful for shedding solar in negative-price periods); defaults to on (PV enabled). Toggling it while a dispatch is running applies immediately; otherwise it takes effect on the next dispatch
- **Battery cell health** - min/max cell voltages polled every 60 s; charge/discharge cutoff voltages, module count, capacity, and type available as diagnostic sensors
- **Dispatch diagnostics** - energy flow direction (human-readable), PV switch state, frequency dispatch flag, power, and frequency
- **Charging / Discharging time periods** - configure up to two charge and discharge windows
- **Dispatch mode selector** - Battery only, SoC Control, Load Following, Maximise Output, and more
- **Max Feed to Grid** - set grid export limit as % of installed PV capacity
- **Date & Time sync** - sync inverter clock to Home Assistant system time
- **Sync Dispatch State** - reconcile HA switch states with the inverter after a restart

---

## Requirements

- AlphaESS inverter with **Modbus TCP enabled** on port 502
- Inverter reachable on your local network (wired LAN or powerline recommended)
- Home Assistant **2024.10 or newer**
- On Home Assistant 2026.10 or older: HACS installed (2026.11 and newer have the Marketplace built in)

### Compatible models reported by users

Some inverters sold under other brands use the same Modbus registers. Users have reported that the integration works with these models. They have not been tested by the project:

- SunPower Reserve One
- Haier E-tower
- ZinVolt Micro

---

## Installation

### Via the Marketplace (Home Assistant 2026.11 and newer)

1. Go to **Settings → Marketplace**
2. Search for **AlphaESS Modbus TCP** and open it
3. Click **Download**
4. Restart Home Assistant

Updates appear in **Settings → Updates**. Beta versions are only offered if you turn on pre-releases for this integration in the Marketplace.

### Via HACS (Home Assistant 2026.10 and older)

1. Open HACS in Home Assistant
2. Search for **AlphaESS Modbus TCP** and open it
3. Click **Download**
4. Restart Home Assistant

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
| Inverter IP Address | - | Use a DHCP reservation for a stable address |
| Modbus Port | `502` | Change only if you've modified the inverter setting |
| Slave ID | `85` | Standard for AlphaESS inverters |

4. Click **Submit** - Home Assistant will test the connection before saving

### Changing the IP address, port or slave ID

If the inverter moves to a new IP address, you do not need to remove and re-add the integration. Go to **Settings → Devices & Services → AlphaESS Modbus TCP**, open the three-dot menu on the entry and choose **Reconfigure**. The new settings are tested before they are saved, and your entities, history and dashboards are kept.

### Multiple Inverters

To run two AlphaESS inverters with the same Home Assistant instance:

1. Add the integration a second time: **Settings → Devices & Services → Add Integration**, search for **AlphaESS Modbus TCP**, and enter the second inverter's IP address.
2. Immediately rename each device so entity IDs reflect the device name: **Settings → Devices & Services → [device] → pencil icon**. For example, rename one to "AlphaESS Roof" and the other to "AlphaESS Garage".
3. Home Assistant updates all entity IDs automatically - `sensor.alphaess_inverter_*` becomes `sensor.alphaess_roof_*` and `sensor.alphaess_garage_*`.
4. Each integration instance maintains its own Modbus TCP connection. The inverter one-connection limit applies per device - the two instances do not share a connection and do not interfere with each other.

---

## Poll Intervals

Each sensor has a base poll interval. The coordinator runs a master loop (2 s by default); contiguous registers due in the same cycle are batched into a single Modbus read. Individual registers are skipped when their own `scan_interval` hasn't elapsed yet.

The base intervals in the table below are the minimum achievable intervals. A register can only be read when the master loop fires, so in Normal mode (2 s loop) the effective floor is 2 s -- the 1 s entries are only read every 1 s when Fast mode is active. Actual intervals also scale with the Poll Mode multiplier (see [Poll Speed](#poll-speed) below).

| Base Interval | Sensors |
|---------------|---------|
| **1 s** | Grid Power, Battery Power, Active Power PV Meter, PV String 1–4 Power, PV Total Power *(disabled by default)* |
| **5 s** | Grid Power Phase A/B/C, Grid Voltage Phase A/B/C, Inverter Work Mode, Inverter Power L1/L2/L3 + total, System Fault, Inverter Warning 1/2, Inverter Fault 1/2, Battery Warning/Fault, Max Feed to Grid, Dispatch registers (including Dispatch Energy Flow Direction, Freq Dispatch Flag), dispatch PV switch, freq dispatch power/frequency *(last two disabled by default)* |
| **10 s** | Battery SoC, Battery SoH, Battery min/max cell temps, Battery max charge/discharge current, Charging Time Period Control, Charging Cutoff SoC |
| **30 s** | Grid Frequency, Charging/Discharging period start/stop times, Discharging Cutoff SoC |
| **60 s** | Inverter Temperature, Battery Voltage/Current/Status, Battery min/max cell voltages, Battery Remaining Time *(disabled)*, Battery relay status *(disabled)*, PV String Voltage & Current, Energy Totals, Version strings, Grid safety registers (OVP/UVP/OFP/UFP) *(disabled)*, Network settings *(disabled)* |
| **300 s** | Battery charge/discharge cutoff voltages, Battery module count, Battery capacity, Battery type *(all disabled by default)* |

### Poll Speed

The integration offers three poll speed presets, configurable via the integration's **Configure** button in Settings → Devices & Services:

| Preset | Coordinator loop | Scan interval multiplier | Use case |
|--------|-----------------|--------------------------|----------|
| Slow | 2 s | 3.0 (configurable) | RS485 converters prone to timeouts; reduces Modbus transaction rate |
| Normal | 2 s | 1.0 (fixed) | Default; suitable for wired LAN |
| Fast | 1 s | 0.5 (configurable) | Tighter real-time control (Excess Export, SoC cutoffs); roughly doubles transaction rate |

The Slow and Fast multipliers can be adjusted in the options form (range 0.25-10.0, step 0.25). Fast mode on low-spec hardware (Raspberry Pi 3 or similar) may impact Home Assistant performance due to the increased polling rate.

### Model Variants

The integration supports two model variants, configurable via the integration's **Configure** button in Settings → Devices & Services:

| Variant | Inverter models |
|---------|----------------|
| Standard | All AlphaESS models except B3/B3PLUS (default) |
| SMILE-B3 / SMILE-B3-PLUS | SMILE-B3 and SMILE-B3-PLUS only |

B3 and B3PLUS inverters report some registers with different scale factors. Selecting the wrong variant will show incorrect values for grid voltage and inverter power registers. If you own a SMILE-B3 or SMILE-B3-PLUS, select that variant after installation.

---

## Entities

### Sensors (read-only)

111 sensors are enabled by default; the remaining 77 are disabled and can be turned on individually in HA under Settings → Devices & Services → [device] → entities. Sensors marked *(disabled)* below are off by default.

#### Power (real-time)

These sensors have a 1 s `scan_interval` but the master loop runs at 2 s in Normal mode, so the effective update rate is 2 s by default. Selecting Fast mode reduces the loop to 1 s, achieving the full 1 s rate.

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Grid Power | W | 2 s (1 s Fast) | Positive = import from grid, negative = export to grid |
| Battery Power | W | 2 s (1 s Fast) | Positive = discharging, negative = charging |
| Active Power PV Meter | W | 2 s (1 s Fast) | PV generation measured at the meter point |
| PV String 1 Power | W | 2 s (1 s Fast) | |
| PV String 2 Power | W | 2 s (1 s Fast) | |
| PV String 3 Power | W | 2 s (1 s Fast) | |
| PV String 4 Power | W | 2 s (1 s Fast) | |
| PV Total Power (Inverter) *(disabled)* | W | 2 s (1 s Fast) | Sum of all PV strings per inverter register 0x0453 |
| Current PV Production | W | calculated | Sum of all PV string powers + PV meter |
| Current House Load | W | calculated | Net house consumption derived from grid, battery, and PV; during a grid outage it comes from PV and battery |
| Excess Power | W | calculated | PV production minus house load, never below 0 |

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
| Inverter Work Mode Name | - | calculated | Work mode as text: Wait, Online, UPS, Bypass, Fault, DC, Self Test, Check, Update Master, Update Slave, Update ARM |
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
| Battery Current | A | 60 s | Pack current; positive = discharging, negative = charging |
| Battery Status | - | 60 s | Human-readable BMS status with raw value, e.g. "Charging + Discharging (257)"; the `charge_state` (0, 1 or 2) and `discharge_state` (0 or 1) attributes split the value into its high and low byte |
| Battery Max Charge Power | W | 10 s | Maximum charge power the BMS allows at present |
| Battery Max Discharge Power | W | 10 s | Maximum discharge power the BMS allows at present |
| Battery SoC Calibration | - | 10 s | BMS SoC calibration flag (1 = enabled, 0 = disabled) |
| Battery Implementation Charge SoC *(disabled)* | % | 60 s | Charge SoC window reported by the BMS; not populated on every model |
| Battery Implementation Discharge SoC *(disabled)* | % | 60 s | Discharge SoC window reported by the BMS; not populated on every model |
| Battery Remaining Charge SoC *(disabled)* | % | 60 s | SoC still available to charge; not populated on every model |
| Battery Remaining Discharge SoC *(disabled)* | % | 60 s | SoC still available to discharge; not populated on every model |
| Battery Single Cut Error Code *(disabled)* | - | 60 s | BMS single cut error code (0 = no error) |
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
| Total Energy Feed to Grid (PV) | kWh | 60 s | Lifetime production of an AC-coupled PV inverter, measured at the PV meter |
| Total Energy PV Inverter Consumption *(disabled)* | kWh | 60 s | Lifetime standby consumption of an AC-coupled PV inverter, measured at the PV meter |
| PV Inverter Energy *(disabled)* | kWh | 60 s | Lifetime AC-coupled PV inverter energy as totalled by the system |
| PV System Total Energy *(disabled)* | kWh | 60 s | Lifetime PV energy of the whole system (inverter strings plus AC-coupled PV inverter) |
| Total Energy Charge Battery | kWh | 60 s | Lifetime energy delivered into battery |
| Total Energy Discharge Battery | kWh | 60 s | Lifetime energy drawn from battery |
| Total Energy Charge Battery from Grid | kWh | 60 s | Lifetime grid-to-battery energy |

#### Daily Energy

These sensors reset each day at midnight using the inverter's lifetime cumulative totals as a baseline. State is preserved across HA restarts. Today's PV Generation also accumulates AC-coupled inverter generation via a Riemann sum; the `ac_accumulated_kwh` attribute on that sensor shows the AC portion separately.

| Entity | Unit | Description |
|--------|------|-------------|
| Today's Energy Feed to Grid | kWh | Energy exported to grid today |
| Today's Energy from Grid | kWh | Energy imported from grid today |
| Today's PV Generation | kWh | Total PV energy generated today (DC strings + AC-coupled) |
| Today's Battery Charged | kWh | Energy delivered into battery today |
| Today's Battery Discharged | kWh | Energy drawn from battery today |
| Today's Battery Charged from Grid | kWh | Grid-to-battery energy today |
| Today's House Load | kWh | Energy used by the house today, integrated from Current House Load |

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
| Dispatch PV Switch | - | 5 s | PV switch state during dispatch |
| Freq Dispatch Power *(disabled)* | W | 5 s | Frequency dispatch power setpoint |
| Freq Dispatch Frequency *(disabled)* | Hz | 5 s | Frequency dispatch trigger frequency |
| Force Charging Countdown | min | 5 s | Live remaining time when Force Charging is active; 0 otherwise |
| Force Discharging Countdown | min | 5 s | Live remaining time when Force Discharging is active; 0 otherwise |
| Force Export Countdown | min | 5 s | Live remaining time when Force Export is active; 0 otherwise |
| Force Import Countdown | min | 5 s | Live remaining time when Force Import is active; 0 otherwise |
| Excess Export Countdown | min | 1 s | Time left before Excess Export turns itself off; unknown when no Excess Export Duration is set |
| Peak Shaving Countdown | min | 1 s | Time left before Peak Shaving turns itself off; unknown when no Peak Shaving Duration is set |

#### Scheduling - Charging / Discharging Periods

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
| BMS Version | - | 60 s | Formatted as V1.65 |
| LMU Version | - | 60 s | Formatted as V1.65 |
| ISO Version | - | 60 s | Formatted as V1.65 |
| EMS Version | - | 60 s | Combined from four sub-registers, e.g. V1.0.23R1 |
| EMS Version High *(disabled)* | - | 60 s | Raw EMS major version component |
| EMS Version Middle *(disabled)* | - | 60 s | |
| EMS Version Low *(disabled)* | - | 60 s | |
| EMS Version Low Suffix *(disabled)* | - | 60 s | |
| System Time YYMM *(disabled)* | - | 5 s | Raw year/month packed register |
| System Time DDHH *(disabled)* | - | 5 s | Raw day/hour packed register |
| System Time MMSS *(disabled)* | - | 5 s | Raw minute/second packed register |

#### Network (all disabled by default)

| Entity | Unit | Poll | Description |
|--------|------|------|-------------|
| Modbus Baud Rate *(disabled)* | - | 60 s | |
| IP Method *(disabled)* | - | 60 s | DHCP or Static |
| Local IP *(disabled)* | - | 60 s | Dotted-decimal IP address, e.g. 10.0.0.209 |
| Subnet Mask *(disabled)* | - | 60 s | Dotted-decimal subnet mask |
| Gateway *(disabled)* | - | 60 s | Dotted-decimal gateway address |

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
| Force Charging Hold | Switch | Keeps Force Charging running indefinitely after the duration expires; turn on before starting Force Charging |
| Force Discharging | Switch | Discharge battery at configured power/duration/cutoff SoC; auto-stops ~1% above cutoff to guarantee no grid draw during transition |
| Force Discharging Hold | Switch | Keeps Force Discharging running for the full configured duration; prevents early stop when the SoC target is reached |
| Force Export | Switch | Hold grid export at a target rate (kW) measured at the grid meter; the battery is adjusted continuously and settles at or slightly above the target, never at a grid import; stops when the duration expires or the battery reaches the Stop at SoC |
| Force Export Hold | Switch | Keeps Force Export running indefinitely after the duration expires; turn on before starting Force Export for continuous export without a time limit |
| Force Import | Switch | Hold grid import at a target rate (kW) measured at the grid meter by adjusting battery charging; settles at or slightly below the target; stops at the Stop at SoC |
| Force Import Hold | Switch | Keeps Force Import running indefinitely after the duration expires; turn on before starting Force Import |
| Force Import Pause | Binary sensor | On when Force Import is automatically paused; resumes automatically when conditions are met |
| Dispatch | Switch | Generic dispatch - mode, power, SoC target, and duration all configurable independently |
| Excess Export | Switch | Charge battery with PV power that would otherwise be clipped by the AC output limit; auto-pauses when house draws from grid, auto-resumes when PV recovers; turns itself off after Excess Export Duration if one is set |
| Excess Export Pause | Binary sensor | On when Excess Export has automatically paused due to grid import |
| Peak Shaving | Switch | Hold grid import at or below Peak Shaving Power by discharging the battery; see Peak Shaving below |
| Peak Shaving Charge Below Limit | Switch | Off (default): the battery only discharges above the limit and idles below it. On: the battery also charges with the headroom, so grid import stays flat at the limit. Kept across restarts |
| Peak Shaving Limited | Binary sensor | On while Peak Shaving is on, the grid is above the limit and the battery cannot discharge more (Stop at SoC, AC limit or BMS limit reached) |
| Peak Shaving Power | Number | Grid import limit in kW (0–30) at the grid meter |
| Peak Shaving Stop at SoC | Number | Peak Shaving does not discharge below this SoC % (default 20) |
| Peak Shaving Duration | Number | Peak Shaving turns itself off after this many minutes (0–480, step 5); 0 = runs until turned off (default) |
| Dispatch PV Enabled | Switch | Enable (on, default) or disable (off) the inverter's PV coupling during dispatch via register 0x088A; toggling while a dispatch is active writes the register immediately, otherwise it applies on the next dispatch |
| Force Charging Power | Number | Charging power in kW (0–20) |
| Force Charging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Charging Stop at SoC | Number | Stop charging at this SoC % |
| Force Discharging Power | Number | Discharging power in kW (0–20) |
| Force Discharging Duration | Number | Duration in minutes (0–480, step 5) |
| Force Discharging Stop at SoC | Number | Stop discharging at this SoC % (switch auto-stops ~1% above this) |
| Force Export Power | Number | Grid export target in kW (0–20) at the grid meter; do not add house load or subtract PV in an automation, the integration does that |
| Force Export Duration | Number | Duration in minutes (0–480, step 5) |
| Force Export Stop at SoC | Number | Stop exporting at this SoC % (switch auto-stops ~1% above this) |
| Force Import Power | Number | Grid import target in kW (0–20) at the grid meter (not the battery charge rate) |
| Force Import Duration | Number | Duration in minutes (0–480, step 5) |
| Force Import Stop at SoC | Number | Stop importing at this SoC % |
| Excess Export Duration | Number | Excess Export turns itself off after this many minutes (0–480, step 5); 0 = runs until turned off (default) |
| Dispatch Power | Number | Dispatch power in kW (−20 to +20; negative = charge, positive = discharge/export); defaults to 0 kW |
| Dispatch Duration | Number | Duration in minutes (0–480, step 5) |
| Dispatch Stop at SoC | Number | SoC target % for the generic Dispatch switch |
| Dispatch Mode | Select | Operating mode for the generic Dispatch switch (Battery Only, SoC Control, Load Following, etc.) |
| Charging / Discharging Settings | Select | Enable/disable time period control (Disable / Grid Charging / Discharge Time Control / Both) |
| Inverter AC Limit | Select | Inverter AC output capacity (3–20 kW) - used by Excess Export to avoid overloading the inverter |
| Max Feed to Grid | Number | Grid export limit (% of PV capacity) |
| Charging Period 1 Start Time | Time | hh:mm - writes hour and minute registers independently |
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

#### Changing Dispatch Parameters While Running

You can adjust Power, Stop at SoC, or Duration for an active Force Charging, Force Discharging, Force Export, Force Import or Dispatch session without toggling the switch; just change the slider.

- A **Power** or **Stop at SoC** change takes effect at once and the countdown keeps running from where it was. For Force Export and Force Import, a power change moves the battery setpoint by the change in target and the control trims from there, so an automation can adjust the target often without disturbing the export.
- A **Duration** change restarts the countdown from the new duration.
- For Excess Export, changing **Excess Export Duration** while it runs moves the stop time without interrupting it.

#### Peak Shaving

Peak Shaving keeps the import measured at the grid meter at or below Peak Shaving Power. When the house draws more than that, the battery supplies the rest, up to the inverter's AC limit and the battery's discharge limit, and never below Peak Shaving Stop at SoC. Typical use: an EV charger that Home Assistant cannot control, or a connection with a capacity limit.

- With **Peak Shaving Charge Below Limit** off, the battery idles while the house is below the limit, so it is kept for the peaks. It does not charge from solar surplus while Peak Shaving is on.
- With it on, the battery also charges when the house uses less than the limit, so grid import stays flat at the limit (useful for charging a car at a fixed grid draw while the battery buffers the difference).
- Peak Shaving is mutually exclusive with the other dispatch controls, and like them it does not resume after a Home Assistant restart. Each command to the inverter lasts 5 minutes and is renewed while Peak Shaving runs, so if Home Assistant stops, the inverter returns to normal operation within 5 minutes. When Home Assistant comes back (or the integration reloads) while that command is still running, the integration ends it straight away.
- **AC-coupled PV:** on at least one system with a separate AC-coupled PV inverter, the PV inverter's output drops to almost nothing whenever the battery is commanded to discharge. If you see that, Peak Shaving will cost you solar production while it is shaving.

#### Tip: deferring battery charging with Excess Export

Beyond preventing clipping, Excess Export keeps battery charging from PV surplus on hold while still letting the battery cover the house when PV drops below demand. On a dynamic tariff you can use this to export solar during a morning price peak and let the battery charge later, for example in a cheaper period around solar noon, when the solar forecast says there will be enough surplus to fill it. Set Excess Export Duration to the length of the peak so it turns itself off and the battery is not left waiting all day.

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
- AlphaESS inverters only allow **one Modbus TCP connection at a time** - if another app (a second HA instance, a Modbus tool, Alpha2MQTT, etc.) is already connected, HA will be refused. Disconnect the other client and reload the integration

**Entities show unavailable after some time**
- This can happen if the inverter goes into sleep/standby mode at night - it recovers automatically when the inverter wakes up
- Check HA logs for Modbus timeout errors

**Force charging / dispatch not working**
- Only one dispatch mode can be active at a time - activating one switch will deactivate any other active switch
- Dispatch automatically resets after the configured duration expires

---

## Advanced: Writing Registers Directly

The `alphaess_modbus.write_register` service writes a raw integer value to any Modbus holding register using FC6 (Write Single Register). It is intended for use from Developer Tools or automations by advanced users and developers.

> **Warning:** Writing incorrect values to grid safety registers (overvoltage, undervoltage, frequency protection) or inverter configuration registers can cause the inverter to trip or behave unexpectedly. Use with care and consult the AlphaESS Modbus register documentation before writing to any register you are not certain about. This service is for developers only.

```yaml
service: alphaess_modbus.write_register
data:
  address: 2052    # register address as a decimal integer (hex: 0x0804)
  value: 400       # raw integer to write (no scale or offset applied)
```

The address must be provided as a decimal integer. Convert hex addresses from the register documentation using a calculator (for example, 0x0804 = 2052). The value is written as-is with no scale or offset applied.

If two inverters are configured, the service writes the same value to all instances.

---

## Dashboards

Example Lovelace dashboard configurations are included in the [`examples/`](examples/) folder:

| File | Description | Custom cards required |
|------|-------------|----------------------|
| `alphaess_dashboard_pfcp.yaml` | Sections-layout dashboard with live power flow diagram - battery controls, scheduling, dispatch, energy stats, system info | [power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus) |
| `alphaess_dashboard.yaml` | Sections-layout dashboard without custom cards - gauge + glance live view, battery controls, scheduling, dispatch, energy stats, system info | None |
| `power_diagram.yaml` | Power flow chart for today | [ApexCharts Card](https://github.com/RomRider/apexcharts-card) |
| `power_diagram_extended.yaml` | Extended power diagrams - today, yesterday, 3-day, string detail, instant, and hi-res views | [ApexCharts Card](https://github.com/RomRider/apexcharts-card) |

### How to use

1. Install any required custom cards via HACS (see table above):
   - **power-flow-card-plus**: HACS → Frontend → search "Power Flow Card Plus" → Download
   - **ApexCharts Card**: HACS → Frontend → search "ApexCharts Card" → Download
2. In Home Assistant go to **Settings → Dashboards → Add Dashboard**
3. Open the view you want to replace, click the three-dot menu → **Edit in YAML**, and paste the contents of the example file directly (the file starts with `title:` - no extra wrapping needed).

4. Reload the dashboard browser tab after installing any custom cards

> **EV Charger entity:** `alphaess_dashboard_pfcp.yaml` includes `sensor.charger_power_active_import` in the power flow diagram. If you do not have an EV charger, remove the `individual:` block from the `custom:power-flow-card-plus` card.

> All entity IDs follow the pattern `sensor.alphaess_inverter_*`, `switch.alphaess_inverter_*`, etc. (the device name is "AlphaESS Inverter", which Home Assistant uses as the entity ID prefix).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Credits

This integration is based on the YAML package developed by **Axel Koegler** and documented at [projects.hillviewlodge.ie/alphaess](https://projects.hillviewlodge.ie/alphaess/). All Modbus register mappings are derived from that work and the AlphaESS Modbus register documentation.

Documentation and release notes assisted by [Claude](https://claude.ai) (Anthropic).

---

## License

MIT - see [LICENSE](LICENSE)
