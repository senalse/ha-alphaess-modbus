# AlphaESS Modbus Register Map

This document is auto-generated from `custom_components/alphaess_modbus/const.py`. Run `python scripts/generate_register_docs.py` from the repo root to regenerate it after modifying any register definitions.

Entity IDs follow the pattern `<platform>.alphaess_<device_name>_<key>` where `<device_name>` is derived from the name you gave the device during setup (e.g. `sensor.alphaess_inverter_soc_battery`).

---

## Contents

- [Sensor Registers](#sensor-registers-read-only)
- [Writable Number Entities](#writable-number-entities)
- [Writable Select Entities](#writable-select-entities)
- [Writable Time Entities](#writable-time-entities)
- [Switch Entities](#switch-entities)
- [Button Entities](#button-entities)
- [Dispatch Register Block](#dispatch-register-block)

---

## Sensor Registers (read-only)

Sensors are polled at the interval shown. Entries marked **off** in the Default column are disabled in HA until manually enabled.

### System

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x041C | `inverter_grid_frequency` | Grid Frequency | AC grid frequency measured at the inverter connection point | Hz | int16 | x0.01 | 30 s | on |
| 0x0435 | `inverter_temperature` | Inverter Temperature | Internal inverter temperature | °C | int16 | x0.1 | 60 s | on |
| 0x0440 | `inverter_work_mode` | Inverter Work Mode | Inverter operating mode (1 = normal, 2 = bypass/EPS; other values are model-specific) | - | int16 | - | 5 s | on |
| 0x064A | `inverter_sn` | Inverter Serial Number | Inverter serial number string | - | string | - | 60 s | on |
| 0x0115 | `bms_version` | BMS Version | Battery Management System firmware version number | - | int16 | - | 60 s | on |
| 0x0116 | `lmu_version` | LMU Version | Lithium Management Unit firmware version number | - | int16 | - | 60 s | on |
| 0x0117 | `iso_version` | ISO Version | ISO board firmware version number | - | int16 | - | 60 s | on |
| 0x0640 | `inverter_version` | Inverter Version | Inverter DSP firmware version string | - | string | - | 60 s | on |
| 0x0645 | `inverter_arm_version` | Inverter ARM Version | Inverter ARM co-processor firmware version string | - | string | - | 60 s | on |
| 0x074B | `ems_version_high` | EMS Version High | EMS firmware version - major component | - | int16 | - | 60 s | off |
| 0x074C | `ems_version_middle` | EMS Version Middle | EMS firmware version - minor component | - | int16 | - | 60 s | off |
| 0x074D | `ems_version_low` | EMS Version Low | EMS firmware version - patch component | - | int16 | - | 60 s | off |
| 0x074F | `ems_version_low_suffix` | EMS Version Low Suffix | EMS firmware version - suffix string | - | string | - | 60 s | off |

### System Time

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0740 | `system_time_yymm` | System Time YYMM | Inverter clock - year and month packed as YYMM integer | - | int16 | - | 5 s | off |
| 0x0741 | `system_time_ddhh` | System Time DDHH | Inverter clock - day and hour packed as DDHH integer | - | int16 | - | 5 s | off |
| 0x0742 | `system_time_mmss` | System Time MMSS | Inverter clock - minute and second packed as MMSS integer | - | int16 | - | 5 s | off |

### Network

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0810 | `modbus_baud_rate` | Modbus Baud Rate | Modbus RS-485 baud rate | - | uint16 | - | 60 s | off |
| 0x0808 | `ip_method` | IP Method | IP address assignment method | - | uint16 | - | 60 s | off |
| 0x0809 | `local_ip` | Local IP | Inverter local IP address as a packed 32-bit integer | - | uint32 | - | 60 s | off |
| 0x080B | `subnet_mask` | Subnet Mask | Inverter subnet mask as a packed 32-bit integer | - | uint32 | - | 60 s | off |
| 0x080D | `gateway` | Gateway | Inverter default gateway as a packed 32-bit integer | - | uint32 | - | 60 s | off |

### Grid Power

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0021 | `power_grid` | Grid Power | Total grid power; positive = importing from grid, negative = exporting to grid | W | int32 | - | 1 s | on |
| 0x001B | `power_phase_a_grid` | Grid Power Phase A | Phase A grid power | W | int32 | - | 5 s | on |
| 0x001D | `power_phase_b_grid` | Grid Power Phase B | Phase B grid power | W | int32 | - | 5 s | on |
| 0x001F | `power_phase_c_grid` | Grid Power Phase C | Phase C grid power | W | int32 | - | 5 s | on |
| 0x0014 | `voltage_phase_a_grid` | Grid Voltage Phase A | Phase A grid voltage | V | int16 | - | 5 s | on |
| 0x0015 | `voltage_phase_b_grid` | Grid Voltage Phase B | Phase B grid voltage | V | int16 | - | 5 s | on |
| 0x0016 | `voltage_phase_c_grid` | Grid Voltage Phase C | Phase C grid voltage | V | int16 | - | 5 s | on |

### Battery Power

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0126 | `power_battery` | Battery Power | Battery charge/discharge power; positive = charging, negative = discharging | W | int16 | - | 1 s | on |

### Inverter Power

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0406 | `power_inverter_l1` | Inverter Power L1 | Inverter AC output power on line 1 | W | int32 | - | 5 s | on |
| 0x0408 | `power_inverter_l2` | Inverter Power L2 | Inverter AC output power on line 2 | W | int32 | - | 5 s | on |
| 0x040A | `power_inverter_l3` | Inverter Power L3 | Inverter AC output power on line 3 | W | int32 | - | 5 s | on |
| 0x040C | `power_inverter` | Inverter Power | Total inverter AC output power across all lines | W | int32 | - | 5 s | on |
| 0x0414 | `backup_power_inverter_l1` | Backup Inverter Power L1 | Backup (EPS/off-grid) output power on line 1 | W | int32 | - | 5 s | off |
| 0x0416 | `backup_power_inverter_l2` | Backup Inverter Power L2 | Backup (EPS/off-grid) output power on line 2 | W | int32 | - | 5 s | off |
| 0x0418 | `backup_power_inverter_l3` | Backup Inverter Power L3 | Backup (EPS/off-grid) output power on line 3 | W | int32 | - | 5 s | off |
| 0x041A | `backup_power_inverter` | Backup Inverter Power | Total backup (EPS/off-grid) output power | W | int32 | - | 5 s | off |

### PV Power

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x00A1 | `active_power_pv_meter` | Active Power PV Meter | PV generation measured at the AC-side PV meter | W | int32 | - | 1 s | on |
| 0x041F | `pv1_power` | PV String 1 Power | DC power from PV string 1 | W | uint32 | - | 1 s | on |
| 0x041D | `pv1_voltage` | PV String 1 Voltage | DC voltage of PV string 1 | V | int16 | x0.1 | 60 s | on |
| 0x041E | `pv1_current` | PV String 1 Current | DC current of PV string 1 | A | int16 | x0.1 | 60 s | on |
| 0x0423 | `pv2_power` | PV String 2 Power | DC power from PV string 2 | W | uint32 | - | 1 s | on |
| 0x0421 | `pv2_voltage` | PV String 2 Voltage | DC voltage of PV string 2 | V | int16 | x0.1 | 60 s | on |
| 0x0422 | `pv2_current` | PV String 2 Current | DC current of PV string 2 | A | int16 | x0.1 | 60 s | on |
| 0x0427 | `pv3_power` | PV String 3 Power | DC power from PV string 3 | W | uint32 | - | 1 s | on |
| 0x0425 | `pv3_voltage` | PV String 3 Voltage | DC voltage of PV string 3 | V | int16 | x0.1 | 60 s | on |
| 0x0426 | `pv3_current` | PV String 3 Current | DC current of PV string 3 | A | int16 | x0.1 | 60 s | on |
| 0x042B | `pv4_power` | PV String 4 Power | DC power from PV string 4 | W | uint32 | - | 1 s | on |
| 0x0429 | `pv4_voltage` | PV String 4 Voltage | DC voltage of PV string 4 | V | int16 | x0.1 | 60 s | on |
| 0x042A | `pv4_current` | PV String 4 Current | DC current of PV string 4 | A | int16 | x0.1 | 60 s | on |
| 0x0453 | `pv_total_power` | PV Total Power (Inverter) | Sum of all PV string DC power as reported by the inverter | W | uint32 | - | 1 s | off |

### Energy Totals

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0010 | `total_energy_feed_to_grid_meter` | Total Energy Feed to Grid (Meter) | Lifetime export energy measured at the grid meter; use this for the HA energy dashboard | kWh | uint32 | x0.01 | 60 s | on |
| 0x0012 | `total_energy_consumption_from_grid_meter` | Total Energy Consumption from Grid (Meter) | Lifetime import energy measured at the grid meter; use this for the HA energy dashboard | kWh | uint32 | x0.01 | 60 s | on |
| 0x0090 | `total_energy_feed_to_grid_pv` | Total Energy Feed to Grid (PV) | Lifetime energy exported from PV, measured at the AC PV meter | kWh | uint32 | x0.01 | 60 s | on |
| 0x0120 | `total_energy_charge_battery` | Total Energy Charge Battery | Lifetime energy delivered to the battery | kWh | uint32 | x0.1 | 60 s | on |
| 0x0122 | `total_energy_discharge_battery` | Total Energy Discharge Battery | Lifetime energy drawn from the battery | kWh | uint32 | x0.1 | 60 s | on |
| 0x0124 | `total_energy_charge_battery_from_grid` | Total Energy Charge Battery from Grid | Lifetime energy used to charge the battery from the grid | kWh | uint32 | x0.1 | 60 s | on |
| 0x043E | `total_energy_from_pv` | Total Energy from PV | Lifetime total PV energy generated | kWh | uint32 | x0.1 | 60 s | on |

### Faults & Warnings

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x08D4 | `system_fault` | System Fault | System-level fault bitmap; non-zero means a fault is active | - | uint32 | - | 5 s | on |
| 0x0436 | `inverter_warning_1` | Inverter Warning 1 | Inverter warning bitmap, word 1 of 2 | - | uint32 | - | 5 s | on |
| 0x0438 | `inverter_warning_2` | Inverter Warning 2 | Inverter warning bitmap, word 2 of 2 | - | uint32 | - | 5 s | on |
| 0x043A | `inverter_fault_1` | Inverter Fault 1 | Inverter fault bitmap, word 1 of 2 | - | uint32 | - | 5 s | on |
| 0x043C | `inverter_fault_2` | Inverter Fault 2 | Inverter fault bitmap, word 2 of 2 | - | uint32 | - | 5 s | on |
| 0x011C | `battery_warning` | Battery Warning | Aggregate battery warning bitmap | - | uint32 | - | 5 s | on |
| 0x011E | `battery_fault` | Battery Fault | Aggregate battery fault bitmap | - | uint32 | - | 5 s | on |
| 0x013D | `battery_1_warning` | Battery 1 Warning | Warning bitmap for battery module 1 | - | uint32 | - | 5 s | off |
| 0x013F | `battery_2_warning` | Battery 2 Warning | Warning bitmap for battery module 2 | - | uint32 | - | 5 s | off |
| 0x0141 | `battery_3_warning` | Battery 3 Warning | Warning bitmap for battery module 3 | - | uint32 | - | 5 s | off |
| 0x0143 | `battery_4_warning` | Battery 4 Warning | Warning bitmap for battery module 4 | - | uint32 | - | 5 s | off |
| 0x0145 | `battery_5_warning` | Battery 5 Warning | Warning bitmap for battery module 5 | - | uint32 | - | 5 s | off |
| 0x0147 | `battery_6_warning` | Battery 6 Warning | Warning bitmap for battery module 6 | - | uint32 | - | 5 s | off |
| 0x0131 | `battery_1_fault` | Battery 1 Fault | Fault bitmap for battery module 1 | - | uint32 | - | 5 s | off |
| 0x0133 | `battery_2_fault` | Battery 2 Fault | Fault bitmap for battery module 2 | - | uint32 | - | 5 s | off |
| 0x0135 | `battery_3_fault` | Battery 3 Fault | Fault bitmap for battery module 3 | - | uint32 | - | 5 s | off |
| 0x0137 | `battery_4_fault` | Battery 4 Fault | Fault bitmap for battery module 4 | - | uint32 | - | 5 s | off |
| 0x0139 | `battery_5_fault` | Battery 5 Fault | Fault bitmap for battery module 5 | - | uint32 | - | 5 s | off |
| 0x013B | `battery_6_fault` | Battery 6 Fault | Fault bitmap for battery module 6 | - | uint32 | - | 5 s | off |

### Grid Safety

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x1000 | `grid_regulation` | Grid Regulation | Active grid compliance standard or regulation profile | - | int16 | - | 60 s | off |
| 0x100B | `ovp_l1` | Overvoltage Protection L1 | Over-voltage protection threshold, level 1 | V | int16 | x0.1 | 60 s | off |
| 0x100C | `ovp_l1_time` | Overvoltage Protection L1 Time | Trip delay for over-voltage protection level 1 | ms | int16 | - | 60 s | off |
| 0x101B | `ovp_l2` | Overvoltage Protection L2 | Over-voltage protection threshold, level 2 | V | int16 | x0.1 | 60 s | off |
| 0x101C | `ovp_l2_time` | Overvoltage Protection L2 Time | Trip delay for over-voltage protection level 2 | ms | int16 | - | 60 s | off |
| 0x101D | `ovp_l3` | Overvoltage Protection L3 | Over-voltage protection threshold, level 3 | V | int16 | x0.1 | 60 s | off |
| 0x101E | `ovp_l3_time` | Overvoltage Protection L3 Time | Trip delay for over-voltage protection level 3 | ms | int16 | - | 60 s | off |
| 0x100D | `ovp10` | Overvoltage Protection 10min | 10-minute average over-voltage protection threshold | V | int16 | x0.1 | 60 s | off |
| 0x100E | `ovp10_time` | Overvoltage Protection 10min Time | Trip delay for 10-minute over-voltage protection | s | int16 | - | 60 s | off |
| 0x100F | `uvp_l1` | Undervoltage Protection L1 | Under-voltage protection threshold, level 1 | V | int16 | x0.1 | 60 s | off |
| 0x1010 | `uvp_l1_time` | Undervoltage Protection L1 Time | Trip delay for under-voltage protection level 1 | ms | int16 | - | 60 s | off |
| 0x1011 | `uvp_l2` | Undervoltage Protection L2 | Under-voltage protection threshold, level 2 | V | int16 | x0.1 | 60 s | off |
| 0x1012 | `uvp_l2_time` | Undervoltage Protection L2 Time | Trip delay for under-voltage protection level 2 | ms | int16 | - | 60 s | off |
| 0x101F | `uvp_l3` | Undervoltage Protection L3 | Under-voltage protection threshold, level 3 | V | int16 | x0.1 | 60 s | off |
| 0x1020 | `uvp_l3_time` | Undervoltage Protection L3 Time | Trip delay for under-voltage protection level 3 | ms | int16 | - | 60 s | off |
| 0x1013 | `ofp_l1` | Overfrequency Protection L1 | Over-frequency protection threshold, level 1 | Hz | int16 | x0.01 | 60 s | off |
| 0x1014 | `ofp_l1_time` | Overfrequency Protection L1 Time | Trip delay for over-frequency protection level 1 | ms | int16 | - | 60 s | off |
| 0x1015 | `ofp_l2` | Overfrequency Protection L2 | Over-frequency protection threshold, level 2 | Hz | int16 | x0.01 | 60 s | off |
| 0x1016 | `ofp_l2_time` | Overfrequency Protection L2 Time | Trip delay for over-frequency protection level 2 | ms | int16 | - | 60 s | off |
| 0x1021 | `ofp_l3` | Overfrequency Protection L3 | Over-frequency protection threshold, level 3 | Hz | int16 | x0.01 | 60 s | off |
| 0x1022 | `ofp_l3_time` | Overfrequency Protection L3 Time | Trip delay for over-frequency protection level 3 | ms | int16 | - | 60 s | off |
| 0x1017 | `ufp_l1` | Underfrequency Protection L1 | Under-frequency protection threshold, level 1 | Hz | int16 | x0.01 | 60 s | off |
| 0x1018 | `ufp_l1_time` | Underfrequency Protection L1 Time | Trip delay for under-frequency protection level 1 | ms | int16 | - | 60 s | off |
| 0x1019 | `ufp_l2` | Underfrequency Protection L2 | Under-frequency protection threshold, level 2 | Hz | int16 | x0.01 | 60 s | off |
| 0x101A | `ufp_l2_time` | Underfrequency Protection L2 Time | Trip delay for under-frequency protection level 2 | ms | int16 | - | 60 s | off |
| 0x1023 | `ufp_l3` | Underfrequency Protection L3 | Under-frequency protection threshold, level 3 | Hz | int16 | x0.01 | 60 s | off |
| 0x1024 | `ufp_l3_time` | Underfrequency Protection L3 Time | Trip delay for under-frequency protection level 3 | ms | int16 | - | 60 s | off |

### Battery

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0102 | `soc_battery` | Battery State of Charge | Battery state of charge | % | int16 | x0.1 | 10 s | on |
| 0x011B | `soh_battery` | Battery State of Health | Battery state of health; 100% indicates a fully healthy pack | % | int16 | x0.1 | 10 s | on |
| 0x0103 | `battery_status` | Battery Status | Battery status code reported by the BMS | - | int16 | - | 60 s | on |
| 0x0100 | `battery_voltage` | Battery Voltage | Battery pack terminal voltage | V | int16 | x0.1 | 60 s | on |
| 0x0101 | `battery_current` | Battery Current | Battery pack current; positive = charging, negative = discharging | A | int16 | x0.1 | 60 s | on |
| 0x010D | `battery_min_cell_temp` | Battery Min Cell Temp | Lowest temperature across all battery cells | °C | uint16 | x0.1 | 10 s | on |
| 0x0110 | `battery_max_cell_temp` | Battery Max Cell Temp | Highest temperature across all battery cells | °C | uint16 | x0.1 | 10 s | on |
| 0x0111 | `battery_max_charge_current` | Battery Max Charge Current | Maximum charge current allowed by the BMS at present | A | uint16 | x0.1 | 10 s | on |
| 0x0112 | `battery_max_discharge_current` | Battery Max Discharge Current | Maximum discharge current allowed by the BMS at present | A | uint16 | x0.1 | 10 s | on |
| 0x0127 | `battery_remaining_time_raw` | Battery Remaining Time (raw) | BMS estimate of time to full charge or discharge | min | int16 | - | 60 s | off |
| 0x0104 | `battery_relay_status` | Battery Relay Status | Battery contactor/relay state bitmap | - | uint16 | - | 60 s | off |
| 0x0107 | `battery_min_cell_voltage` | Battery Min Cell Voltage | Voltage of the lowest cell in the pack; watch for cell imbalance | V | uint16 | x0.001 | 60 s | on |
| 0x010A | `battery_max_cell_voltage` | Battery Max Cell Voltage | Voltage of the highest cell in the pack; watch for cell imbalance | V | uint16 | x0.001 | 60 s | on |
| 0x0113 | `battery_charge_cutoff_voltage` | Battery Charge Cutoff Voltage | Pack voltage at which the BMS stops charging | V | uint16 | x0.1 | 300 s | off |
| 0x0114 | `battery_discharge_cutoff_voltage` | Battery Discharge Cutoff Voltage | Pack voltage at which the BMS stops discharging | V | uint16 | x0.1 | 300 s | off |
| 0x0118 | `battery_module_count` | Battery Module Count | Number of battery modules in the installed pack | - | uint16 | - | 300 s | off |
| 0x0119 | `battery_capacity_kwh` | Battery Capacity | Total rated capacity of the installed battery pack | kWh | uint16 | x0.1 | 300 s | off |
| 0x011A | `battery_type` | Battery Type | Battery chemistry or model type code | - | uint16 | - | 300 s | off |

### PV Settings

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0800 | `max_feed_to_grid` | Max Feed to Grid | Maximum export power as a percentage of inverter AC capacity; also writable via number entity | % | uint16 | - | 5 s | on |
| 0x0801 | `pv_capacity_storage` | PV Capacity Storage | Configured DC PV capacity connected to the storage inverter | W | uint32 | - | 60 s | off |
| 0x0803 | `pv_capacity_grid_inverter` | PV Capacity of Grid Inverter | Configured DC PV capacity connected to the grid-tied inverter | W | uint32 | - | 60 s | off |

### Grid Meter

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0001 | `ct_rate_grid_meter` | CT Rate Grid Meter | Current transformer ratio configured for the grid power meter | - | uint16 | - | 60 s | off |
| 0x0081 | `ct_rate_pv_meter` | CT Rate PV Meter | Current transformer ratio configured for the PV power meter | - | uint16 | - | 60 s | off |

### Charge Schedule

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x084F | `charging_time_period_control` | Charging Time Period Control | Bitmask enabling grid charging and/or discharge time windows; also writable via select entity | - | int16 | - | 10 s | on |
| 0x0855 | `charging_cutoff_soc` | Charging Cutoff SoC | SoC at which scheduled grid charging stops; also writable via number entity | % | int16 | - | 10 s | on |
| 0x0856 | `charging_period_1_start_hour` | Charging Period 1 Start Hour | Hour component of charging window 1 start time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0857 | `charging_period_1_stop_hour` | Charging Period 1 Stop Hour | Hour component of charging window 1 stop time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0858 | `charging_period_2_start_hour` | Charging Period 2 Start Hour | Hour component of charging window 2 start time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0859 | `charging_period_2_stop_hour` | Charging Period 2 Stop Hour | Hour component of charging window 2 stop time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x085E | `charging_period_1_start_minute` | Charging Period 1 Start Minute | Minute component of charging window 1 start time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x085F | `charging_period_1_stop_minute` | Charging Period 1 Stop Minute | Minute component of charging window 1 stop time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x0860 | `charging_period_2_start_minute` | Charging Period 2 Start Minute | Minute component of charging window 2 start time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x0861 | `charging_period_2_stop_minute` | Charging Period 2 Stop Minute | Minute component of charging window 2 stop time; also writable via time entity | min | int16 | - | 30 s | on |

### Discharge Schedule

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0850 | `discharging_cutoff_soc` | Discharging Cutoff SoC | SoC at which scheduled battery discharge stops; also writable via number entity | % | int16 | - | 30 s | on |
| 0x0851 | `discharging_period_1_start_hour` | Discharging Period 1 Start Hour | Hour component of discharge window 1 start time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0852 | `discharging_period_1_stop_hour` | Discharging Period 1 Stop Hour | Hour component of discharge window 1 stop time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0853 | `discharging_period_2_start_hour` | Discharging Period 2 Start Hour | Hour component of discharge window 2 start time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x0854 | `discharging_period_2_stop_hour` | Discharging Period 2 Stop Hour | Hour component of discharge window 2 stop time; also writable via time entity | h | int16 | - | 30 s | on |
| 0x085A | `discharging_period_1_start_minute` | Discharging Period 1 Start Minute | Minute component of discharge window 1 start time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x085B | `discharging_period_1_stop_minute` | Discharging Period 1 Stop Minute | Minute component of discharge window 1 stop time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x085C | `discharging_period_2_start_minute` | Discharging Period 2 Start Minute | Minute component of discharge window 2 start time; also writable via time entity | min | int16 | - | 30 s | on |
| 0x085D | `discharging_period_2_stop_minute` | Discharging Period 2 Stop Minute | Minute component of discharge window 2 stop time; also writable via time entity | min | int16 | - | 30 s | on |

### Dispatch State

| Address | Key | Name | Description | Unit | Type | Scale/Offset | Poll | Default |
|---------|-----|------|-------------|------|------|--------------|------|---------|
| 0x0880 | `dispatch_start` | Dispatch Start | Dispatch active flag; 1 = dispatch running, 0 = idle | - | int16 | - | 5 s | on |
| 0x0881 | `dispatch_active_power` | Dispatch Active Power | Active power setpoint in the current dispatch command; positive = discharge/export, negative = charge/import (offset-corrected from the raw 32000-bias encoding) | W | int32 | offset -32000 | 5 s | on |
| 0x0883 | `dispatch_reactive_power` | Dispatch Reactive Power | Reactive power setpoint in the current dispatch command (offset-corrected from raw 32000-bias encoding) | W | int32 | offset -32000 | 5 s | on |
| 0x0885 | `dispatch_mode` | Dispatch Mode | Control mode for the active dispatch command | - | int16 | - | 5 s | on |
| 0x0886 | `dispatch_soc` | Dispatch SoC | SoC target in the current dispatch command, converted from raw to percent | % | int16 | x0.392 | 5 s | on |
| 0x0887 | `dispatch_time` | Dispatch Time | Time register for the current dispatch command; raw 32-bit value in seconds | - | uint32 | - | 5 s | on |
| 0x0889 | `dispatch_energy_flow_direction` | Dispatch Energy Flow Direction | Energy flow direction code reported by the dispatch subsystem | - | uint16 | - | 5 s | on |
| 0x088A | `dispatch_pv_switch` | Dispatch PV Switch | PV coupling flag in the dispatch control block | - | uint16 | - | 5 s | on |
| 0x088F | `freq_dispatch_flag` | Freq Dispatch Flag | Indicates whether frequency-responsive dispatch is enabled | - | uint16 | - | 5 s | on |
| 0x0890 | `freq_dispatch_power` | Freq Dispatch Power | Power setpoint for frequency-responsive dispatch events | W | int16 | - | 5 s | off |
| 0x0891 | `freq_dispatch_frequency` | Freq Dispatch Frequency | Frequency threshold that triggers frequency-responsive dispatch | Hz | uint16 | x0.01 | 5 s | off |

---

## Writable Number Entities

Numbers with an address write directly to a Modbus register when changed. Numbers with address **N/A** are dispatch parameters -- they are held in memory and assembled into the 11-register dispatch sequence when a switch is turned on.

| Address | Key | Name | Description | Unit | Range | Step |
|---------|-----|------|-------------|------|-------|------|
| 0x0855 | `charging_cutoff_soc` | Charging Cutoff SoC | SoC at which scheduled grid charging stops; live value is read back from the register on each poll | % | 10 - 100 | 1 |
| 0x0850 | `discharging_cutoff_soc` | Discharging Cutoff SoC | SoC at which scheduled battery discharge stops; live value is read back from the register on each poll | % | 4 - 100 | 1 |
| 0x0800 | `max_feed_to_grid` | Max Feed to Grid | Maximum export power as a percentage of inverter AC capacity; live value is read back from the register on each poll | % | 0 - 100 | 1 |
| N/A | `force_charging_cutoff_soc` | Force Charging Stop at SoC | Force Charging stops when battery reaches this SoC (dispatch parameter, not written directly to a register) | % | 4 - 100 | 1 |
| N/A | `force_charging_duration` | Force Charging Duration | Maximum time Force Charging runs before auto-stopping (dispatch parameter) | min | 0 - 480 | 5 |
| N/A | `force_charging_power` | Force Charging Power | Target charge power for Force Charging, capped to inverter AC limit (dispatch parameter) | kW | 0 - 20 | 0.1 |
| N/A | `force_discharging_cutoff_soc` | Force Discharging Stop at SoC | Force Discharging stops when battery falls to this SoC (dispatch parameter) | % | 4 - 100 | 1 |
| N/A | `force_discharging_duration` | Force Discharging Duration | Maximum time Force Discharging runs before auto-stopping (dispatch parameter) | min | 0 - 480 | 5 |
| N/A | `force_discharging_power` | Force Discharging Power | Target discharge power for Force Discharging, capped to inverter AC limit (dispatch parameter) | kW | 0 - 20 | 0.1 |
| N/A | `force_export_cutoff_soc` | Force Export Stop at SoC | Force Export stops when battery falls to this SoC (dispatch parameter) | % | 4 - 100 | 1 |
| N/A | `force_export_duration` | Force Export Duration | Maximum time Force Export runs before auto-stopping (dispatch parameter) | min | 0 - 480 | 5 |
| N/A | `force_export_power` | Force Export Power | Target grid export level for Force Export; the integration adds house load and subtracts PV to derive the battery dispatch value (dispatch parameter) | kW | 0 - 20 | 0.1 |
| N/A | `dispatch_cutoff_soc` | Dispatch Stop at SoC | Generic Dispatch stops when battery reaches this SoC in mode 2 (SoC Control) (dispatch parameter) | % | 4 - 100 | 1 |
| N/A | `dispatch_duration` | Dispatch Duration | Maximum time Generic Dispatch runs before auto-stopping (dispatch parameter) | min | 0 - 480 | 5 |
| N/A | `dispatch_power` | Dispatch Power | Power setpoint for Generic Dispatch; positive = discharge/export, negative = charge/import (dispatch parameter) | kW | -20 - 20 | 0.1 |
| N/A | `force_import_cutoff_soc` | Force Import Stop at SoC | Force Import stops when battery reaches this SoC (dispatch parameter) | % | 4 - 100 | 1 |
| N/A | `force_import_duration` | Force Import Duration | Maximum time Force Import runs before auto-stopping (dispatch parameter) | min | 0 - 480 | 5 |
| N/A | `force_import_power` | Force Import Power | Target grid import level for Force Import; the integration subtracts PV and adds house load to derive the battery charge value (dispatch parameter) | kW | 0 - 20 | 0.1 |

---

## Writable Select Entities

| Address | Key | Name | Description | Options |
|---------|-----|------|-------------|---------|
| 0x084F | `charging_discharging_settings` | Charging / Discharging Settings | Enables or disables the scheduled grid charging and discharge time windows | Disable / Enable Grid Charging Battery / Enable Battery Discharge Time Control / Enable Grid Charging Battery & Battery Discharge Time Control |
| 0x0885 | `dispatch_mode` | Dispatch Mode | Selects the control algorithm used when a dispatch switch is active | Battery only Charges from PV (1) / State of Charge Control (2) / Load Following (3) / Maximise Output (4) / Normal Mode (5) / Optimise Consumption (6) / Maximise Consumption (7) / No Battery Charge (19) |
| N/A | `inverter_ac_limit` | Inverter AC Limit | Inverter AC output rating; used to calculate battery power needed for Force Export and Excess Export | 3 kW / 4 kW / 4.6 kW / 5 kW / 6 kW / 8 kW / 10 kW / 12 kW / 15 kW / 20 kW |

---

## Writable Time Entities

Each time entity writes to two separate registers (hour and minute) when the time is set in HA.

| Hour Addr | Minute Addr | Key | Name | Description |
|-----------|-------------|-----|------|-------------|
| 0x0856 | 0x085E | `charging_period_1_start` | Charging Period 1 Start Time | Start time of scheduled grid charging window 1 (writes hour and minute as two separate registers) |
| 0x0857 | 0x085F | `charging_period_1_stop` | Charging Period 1 Stop Time | Stop time of scheduled grid charging window 1 |
| 0x0858 | 0x0860 | `charging_period_2_start` | Charging Period 2 Start Time | Start time of scheduled grid charging window 2 |
| 0x0859 | 0x0861 | `charging_period_2_stop` | Charging Period 2 Stop Time | Stop time of scheduled grid charging window 2 |
| 0x0851 | 0x085A | `discharging_period_1_start` | Discharging Period 1 Start Time | Start time of scheduled battery discharge window 1 |
| 0x0852 | 0x085B | `discharging_period_1_stop` | Discharging Period 1 Stop Time | Stop time of scheduled battery discharge window 1 |
| 0x0853 | 0x085C | `discharging_period_2_start` | Discharging Period 2 Start Time | Start time of scheduled battery discharge window 2 |
| 0x0854 | 0x085D | `discharging_period_2_stop` | Discharging Period 2 Stop Time | Stop time of scheduled battery discharge window 2 |

---

## Switch Entities

The six dispatch switches (Force Charging, Force Discharging, Force Export, Force Import, Dispatch, Excess Export) are mutually exclusive -- turning one on turns all others off. The four Hold switches are independent gating controls.

| Key | Name | Description |
|-----|------|-------------|
| `force_charging` | Force Charging | Charges the battery at the configured power level; stops at the cutoff SoC, after the duration, or when battery power drops to near zero (unless Force Charging Hold is on) |
| `force_charging_hold` | Force Charging Hold | Prevents Force Charging from auto-stopping when battery power nears zero; useful when the inverter reduces charging before reaching the SoC target |
| `force_discharging` | Force Discharging | Discharges the battery at the configured power level; stops at the cutoff SoC or after the duration |
| `force_discharging_hold` | Force Discharging Hold | Prevents Force Discharging from auto-stopping when battery power nears zero |
| `force_export` | Force Export | Exports power to the grid at the configured level; dynamically adjusts battery dispatch to account for live house load and PV production, refreshing every 25 seconds |
| `force_export_hold` | Force Export Hold | Prevents Force Export from auto-stopping when battery power nears zero |
| `force_import` | Force Import | Charges the battery using grid import at the configured level; accounts for live house load and PV, refreshing every 25 seconds |
| `force_import_hold` | Force Import Hold | Prevents Force Import from auto-stopping when battery power nears zero |
| `dispatch` | Dispatch | Sends a generic dispatch command with the configured power, mode, SoC target, and duration |
| `excess_export` | Excess Export | Exports battery power equal to DC PV clipping (DC PV output minus inverter AC capacity); auto-pauses when importing from grid and resumes when conditions allow |

---

## Button Entities

| Key | Name | Description |
|-----|------|-------------|
| `dispatch_reset` | Dispatch Reset | Writes the dispatch stop command; returns the inverter to its configured scheduled operating mode |
| `synchronise_date_time` | Synchronise Date & Time | Sets the inverter real-time clock to match the current Home Assistant system time |
| `sync_dispatch_state` | Sync Dispatch State | Reads live dispatch registers and corrects HA switch states to match; useful after a HA restart if a dispatch was active when HA stopped |
| `restart_pcs` | Restart PCS | Restarts the Power Conversion System by writing code 7 to the reset register; use with caution |
| `restart_ems` | Restart EMS | Restarts the Energy Management System by writing code 8 to the reset register; use with caution |
| `reset_energy_totals` | Reset Energy Totals | Clears all lifetime energy counters by writing code 1 to the reset register; this is irreversible |

---

## Dispatch Register Block

The dispatch switches write 11 consecutive registers starting at **0x0880**. The active-power field uses a 32000-bias encoding: values below 32000 are charge (battery draw from grid/PV), values above 32000 are discharge (battery output to loads/grid).

| Offset | Address | Field | Encoding |
|--------|---------|-------|----------|
| 0 | 0x0880 | Start | 1 = start, 0 = stop |
| 1 | 0x0881 | Active Power HI | Always 0 (32-bit big-endian split) |
| 2 | 0x0882 | Active Power LO | 32000 - W = charge; 32000 + W = discharge |
| 3 | 0x0883 | Reactive Power HI | Always 0 |
| 4 | 0x0884 | Reactive Power LO | 32000 (neutral) |
| 5 | 0x0885 | Mode | 2 = SoC Control, 3 = Load Following, etc. |
| 6 | 0x0886 | SoC | soc_percent / 0.392 (integer) |
| 7 | 0x0887 | Time HI | Always 0 |
| 8 | 0x0888 | Time LO | Duration in seconds |
| 9 | 0x0889 | Flow Direction | Always 255 |
| 10 | 0x088A | PV Switch | 1 = PV on, 2 = PV off, 0 = leave unchanged |
