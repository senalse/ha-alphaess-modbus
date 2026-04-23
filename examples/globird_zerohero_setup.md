# GloBird ZeroHero Plan Setup

Free grid import: 11:00am – 2:00pm daily
Evening rebate: 6:00pm – 8:00pm (keep grid imports < 0.03 kWh/hour)
Feed-in tariff: $0.15/kWh between 6:00pm – 9:00pm

---

## One-Time Integration Settings

Set these once in the AlphaESS dashboard (Schedule & Settings section):

| Entity | Value |
|---|---|
| Charging / Discharging Settings | Enable Grid Charging Battery |
| Charging Cutoff SoC | 90% |
| Discharging Cutoff SoC | 20% |
| Max Feed to Grid | 100 |
| Inverter AC Limit | 5 kW |
| Charging Period 1 Start Hour | 11 |
| Charging Period 1 Start Minute | 0 |
| Charging Period 1 Stop Hour | 14 |
| Charging Period 1 Stop Minute | 0 |

The inverter automatically charges from the free grid window every day — no automation needed for this.

## Force Export Parameters

Set these once in the Battery Controls → Export section:

| Entity | Value |
|---|---|
| Force Export Power | 3.5 kW |
| Force Export Duration | 180 min |
| Force Export Cutoff SoC | 20% |

## Always-On Switch

Turn this on once and leave it:

| Entity | Value |
|---|---|
| Excess Export switch | On |

---

## HA Automation — Evening Export 6–9pm

Settings → Automations → Add → Edit in YAML:

```yaml
alias: AlphaESS - Evening export 6pm
description: Force export battery during GloBird $0.15 FiT window (6-9pm)
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: numeric_state
    entity_id: sensor.alphaess_inverter_battery_state_of_charge
    above: 25
action:
  - service: switch.turn_on
    target:
      entity_id: switch.alphaess_inverter_force_export
  - delay: "03:00:00"
  - service: switch.turn_off
    target:
      entity_id: switch.alphaess_inverter_force_export
mode: single
```

The condition skips export on cloudy days when battery is below 25%.
The 3-hour delay turns the switch off cleanly at 9pm.
The inverter also self-cancels after 180 min via its own timer.

---

## How It Works Each Day

```
11:00am   Inverter charges from free grid (+ solar tops up too)
 2:00pm   Charging window closes, battery at ~90%
 6:00pm   HA automation triggers force export
           → battery covers house load
           → surplus exports to grid at $0.15/kWh
 9:00pm   Automation turns switch off, inverter self-cancels
 9pm+     Battery covers overnight loads down to 20% floor
11:00am   Cycle repeats
```

---

## Manual Override

If the battery is low before 6pm (cloudy day), manually trigger from the dashboard:
- Check battery SoC first
- Flip Force Export switch manually if above ~30%
- Or skip the day and let the grid cover evening loads
