from __future__ import annotations
from dataclasses import dataclass, field

DOMAIN = "alphaess_modbus"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 85
PLATFORMS = ["binary_sensor", "sensor", "number", "select", "switch", "button", "time"]

# ---------------------------------------------------------------------------
# Register definition dataclasses
# ---------------------------------------------------------------------------
# HOW TO UPDATE FROM YAML:
#   Each HA Modbus sensor block maps to one ModbusSensorDef entry.
#   - address:       hex value from YAML (e.g. 0x0102)
#   - data_type:     "int16" | "uint16" | "int32" | "uint32" | "string"
#   - count:         register count for string types
#   - scale:         YAML scale factor (applied after offset)
#   - offset:        YAML offset (raw_value + offset, then * scale)
#   - scan_interval: seconds between polls for this register
#   - unit / device_class / state_class: same as HA sensor attributes
#   - precision:     decimal places (None = no rounding)
#   - description:   human-readable description for docs/register_map.md
#   - group:         section heading in docs/register_map.md
# ---------------------------------------------------------------------------

@dataclass
class ModbusSensorDef:
    key: str
    name: str
    address: int
    data_type: str
    count: int = 1
    unit: str | None = None
    device_class: str | None = None
    state_class: str = "measurement"
    scale: float = 1.0
    precision: int | None = None
    scan_interval: int = 30
    offset: float = 0.0
    enabled_by_default: bool = True
    description: str = ""
    group: str = ""


@dataclass
class ModbusNumberDef:
    key: str
    name: str
    address: int | None
    data_type: str = "uint16"
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    unit: str | None = None
    mode: str = "slider"
    icon: str | None = None
    ac_limit_scaled: bool = False
    default_value: float | None = None
    description: str = ""


@dataclass
class ModbusSelectDef:
    key: str
    name: str
    address: int | None
    options: list[str] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    icon: str | None = None
    sensor_key: str | None = None  # coordinator.data key holding the raw value for this select
    description: str = ""


@dataclass
class ModbusTimeDef:
    key: str
    name: str
    hour_address: int
    minute_address: int
    icon: str = "mdi:clock-outline"
    description: str = ""


# ---------------------------------------------------------------------------
# SENSOR REGISTERS
# Source: integration_alpha_ess.yaml v10.5
# ---------------------------------------------------------------------------
SENSOR_REGISTERS: list[ModbusSensorDef] = [
    # --- Measurements: system ---
    ModbusSensorDef("inverter_grid_frequency", "Grid Frequency",
                    0x041C, "int16", unit="Hz", device_class="frequency",
                    scale=0.01, precision=2, scan_interval=30,
                    description="AC grid frequency measured at the inverter connection point",
                    group="System"),
    ModbusSensorDef("inverter_temperature", "Inverter Temperature",
                    0x0435, "int16", unit="°C", device_class="temperature",
                    scale=0.1, precision=0, scan_interval=60,
                    description="Internal inverter temperature",
                    group="System"),
    ModbusSensorDef("inverter_work_mode", "Inverter Work Mode",
                    0x0440, "int16", precision=0, scan_interval=5,
                    description="Inverter operating mode (1 = normal, 2 = bypass/EPS; other values are model-specific)",
                    group="System"),
    ModbusSensorDef("inverter_sn", "Inverter Serial Number",
                    0x064A, "string", count=15, scan_interval=60,
                    state_class=None,
                    description="Inverter serial number string",
                    group="System"),
    ModbusSensorDef("bms_version", "BMS Version",
                    0x0115, "int16", precision=0, scan_interval=60,
                    state_class=None,
                    description="Battery Management System firmware version number",
                    group="System"),
    ModbusSensorDef("lmu_version", "LMU Version",
                    0x0116, "int16", precision=0, scan_interval=60,
                    state_class=None,
                    description="Lithium Management Unit firmware version number",
                    group="System"),
    ModbusSensorDef("iso_version", "ISO Version",
                    0x0117, "int16", precision=0, scan_interval=60,
                    state_class=None,
                    description="ISO board firmware version number",
                    group="System"),
    ModbusSensorDef("inverter_version", "Inverter Version",
                    0x0640, "string", count=5, scan_interval=60,
                    state_class=None,
                    description="Inverter DSP firmware version string",
                    group="System"),
    ModbusSensorDef("inverter_arm_version", "Inverter ARM Version",
                    0x0645, "string", count=5, scan_interval=60,
                    state_class=None,
                    description="Inverter ARM co-processor firmware version string",
                    group="System"),
    ModbusSensorDef("ems_version_high", "EMS Version High",
                    0x074B, "int16", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="EMS firmware version - major component",
                    group="System"),
    ModbusSensorDef("ems_version_middle", "EMS Version Middle",
                    0x074C, "int16", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="EMS firmware version - minor component",
                    group="System"),
    ModbusSensorDef("ems_version_low", "EMS Version Low",
                    0x074D, "int16", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="EMS firmware version - patch component",
                    group="System"),
    ModbusSensorDef("ems_version_low_suffix", "EMS Version Low Suffix",
                    0x074F, "string", count=3, scan_interval=60,
                    state_class=None, enabled_by_default=False,
                    description="EMS firmware version - suffix string",
                    group="System"),

    # --- System time ---
    ModbusSensorDef("system_time_yymm", "System Time YYMM",
                    0x0740, "int16", precision=0, scan_interval=5,
                    enabled_by_default=False,
                    description="Inverter clock - year and month packed as YYMM integer",
                    group="System Time"),
    ModbusSensorDef("system_time_ddhh", "System Time DDHH",
                    0x0741, "int16", precision=0, scan_interval=5,
                    enabled_by_default=False,
                    description="Inverter clock - day and hour packed as DDHH integer",
                    group="System Time"),
    ModbusSensorDef("system_time_mmss", "System Time MMSS",
                    0x0742, "int16", precision=0, scan_interval=5,
                    enabled_by_default=False,
                    description="Inverter clock - minute and second packed as MMSS integer",
                    group="System Time"),

    # --- Network ---
    ModbusSensorDef("modbus_baud_rate", "Modbus Baud Rate",
                    0x0810, "uint16", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="Modbus RS-485 baud rate",
                    group="Network"),
    ModbusSensorDef("ip_method", "IP Method",
                    0x0808, "uint16", scan_interval=60,
                    state_class=None, enabled_by_default=False,
                    description="IP address assignment method",
                    group="Network"),
    ModbusSensorDef("local_ip", "Local IP",
                    0x0809, "uint32", scan_interval=60,
                    state_class=None, enabled_by_default=False,
                    description="Inverter local IP address as a packed 32-bit integer",
                    group="Network"),
    ModbusSensorDef("subnet_mask", "Subnet Mask",
                    0x080B, "uint32", scan_interval=60,
                    state_class=None, enabled_by_default=False,
                    description="Inverter subnet mask as a packed 32-bit integer",
                    group="Network"),
    ModbusSensorDef("gateway", "Gateway",
                    0x080D, "uint32", scan_interval=60,
                    state_class=None, enabled_by_default=False,
                    description="Inverter default gateway as a packed 32-bit integer",
                    group="Network"),

    # --- Power: grid ---
    ModbusSensorDef("power_grid", "Grid Power",
                    0x0021, "int32", unit="W", device_class="power",
                    scan_interval=1,
                    description="Total grid power; positive = importing from grid, negative = exporting to grid",
                    group="Grid Power"),
    ModbusSensorDef("power_phase_a_grid", "Grid Power Phase A",
                    0x001B, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Phase A grid power",
                    group="Grid Power"),
    ModbusSensorDef("power_phase_b_grid", "Grid Power Phase B",
                    0x001D, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Phase B grid power",
                    group="Grid Power"),
    ModbusSensorDef("power_phase_c_grid", "Grid Power Phase C",
                    0x001F, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Phase C grid power",
                    group="Grid Power"),
    ModbusSensorDef("voltage_phase_a_grid", "Grid Voltage Phase A",
                    0x0014, "int16", unit="V", device_class="voltage",
                    scan_interval=5,
                    description="Phase A grid voltage",
                    group="Grid Power"),
    ModbusSensorDef("voltage_phase_b_grid", "Grid Voltage Phase B",
                    0x0015, "int16", unit="V", device_class="voltage",
                    scan_interval=5,
                    description="Phase B grid voltage",
                    group="Grid Power"),
    ModbusSensorDef("voltage_phase_c_grid", "Grid Voltage Phase C",
                    0x0016, "int16", unit="V", device_class="voltage",
                    scan_interval=5,
                    description="Phase C grid voltage",
                    group="Grid Power"),

    # --- Power: battery ---
    ModbusSensorDef("power_battery", "Battery Power",
                    0x0126, "int16", unit="W", device_class="power",
                    scan_interval=1,
                    description="Battery charge/discharge power; positive = charging, negative = discharging",
                    group="Battery Power"),

    # --- Power: inverter ---
    ModbusSensorDef("power_inverter_l1", "Inverter Power L1",
                    0x0406, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Inverter AC output power on line 1",
                    group="Inverter Power"),
    ModbusSensorDef("power_inverter_l2", "Inverter Power L2",
                    0x0408, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Inverter AC output power on line 2",
                    group="Inverter Power"),
    ModbusSensorDef("power_inverter_l3", "Inverter Power L3",
                    0x040A, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Inverter AC output power on line 3",
                    group="Inverter Power"),
    ModbusSensorDef("power_inverter", "Inverter Power",
                    0x040C, "int32", unit="W", device_class="power",
                    scan_interval=5,
                    description="Total inverter AC output power across all lines",
                    group="Inverter Power"),
    ModbusSensorDef("backup_power_inverter_l1", "Backup Inverter Power L1",
                    0x0414, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False,
                    description="Backup (EPS/off-grid) output power on line 1",
                    group="Inverter Power"),
    ModbusSensorDef("backup_power_inverter_l2", "Backup Inverter Power L2",
                    0x0416, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False,
                    description="Backup (EPS/off-grid) output power on line 2",
                    group="Inverter Power"),
    ModbusSensorDef("backup_power_inverter_l3", "Backup Inverter Power L3",
                    0x0418, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False,
                    description="Backup (EPS/off-grid) output power on line 3",
                    group="Inverter Power"),
    ModbusSensorDef("backup_power_inverter", "Backup Inverter Power",
                    0x041A, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False,
                    description="Total backup (EPS/off-grid) output power",
                    group="Inverter Power"),

    # --- Power: PV ---
    ModbusSensorDef("active_power_pv_meter", "Active Power PV Meter",
                    0x00A1, "int32", unit="W", device_class="power",
                    scan_interval=1,
                    description="PV generation measured at the AC-side PV meter",
                    group="PV Power"),
    ModbusSensorDef("pv1_power", "PV String 1 Power",
                    0x041F, "uint32", unit="W", device_class="power",
                    scan_interval=1,
                    description="DC power from PV string 1",
                    group="PV Power"),
    ModbusSensorDef("pv1_voltage", "PV String 1 Voltage",
                    0x041D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60,
                    description="DC voltage of PV string 1",
                    group="PV Power"),
    ModbusSensorDef("pv1_current", "PV String 1 Current",
                    0x041E, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60,
                    description="DC current of PV string 1",
                    group="PV Power"),
    ModbusSensorDef("pv2_power", "PV String 2 Power",
                    0x0423, "uint32", unit="W", device_class="power",
                    scan_interval=1,
                    description="DC power from PV string 2",
                    group="PV Power"),
    ModbusSensorDef("pv2_voltage", "PV String 2 Voltage",
                    0x0421, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60,
                    description="DC voltage of PV string 2",
                    group="PV Power"),
    ModbusSensorDef("pv2_current", "PV String 2 Current",
                    0x0422, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60,
                    description="DC current of PV string 2",
                    group="PV Power"),
    ModbusSensorDef("pv3_power", "PV String 3 Power",
                    0x0427, "uint32", unit="W", device_class="power",
                    scan_interval=1,
                    description="DC power from PV string 3",
                    group="PV Power"),
    ModbusSensorDef("pv3_voltage", "PV String 3 Voltage",
                    0x0425, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60,
                    description="DC voltage of PV string 3",
                    group="PV Power"),
    ModbusSensorDef("pv3_current", "PV String 3 Current",
                    0x0426, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60,
                    description="DC current of PV string 3",
                    group="PV Power"),
    ModbusSensorDef("pv4_power", "PV String 4 Power",
                    0x042B, "uint32", unit="W", device_class="power",
                    scan_interval=1,
                    description="DC power from PV string 4",
                    group="PV Power"),
    ModbusSensorDef("pv4_voltage", "PV String 4 Voltage",
                    0x0429, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60,
                    description="DC voltage of PV string 4",
                    group="PV Power"),
    ModbusSensorDef("pv4_current", "PV String 4 Current",
                    0x042A, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60,
                    description="DC current of PV string 4",
                    group="PV Power"),
    ModbusSensorDef("pv_total_power", "PV Total Power (Inverter)",
                    0x0453, "uint32", unit="W", device_class="power",
                    scan_interval=1, enabled_by_default=False,
                    description="Sum of all PV string DC power as reported by the inverter",
                    group="PV Power"),

    # --- Energy totals ---
    ModbusSensorDef("total_energy_feed_to_grid_meter", "Total Energy Feed to Grid (Meter)",
                    0x0010, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60,
                    description="Lifetime export energy measured at the grid meter; use this for the HA energy dashboard",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_consumption_from_grid_meter", "Total Energy Consumption from Grid (Meter)",
                    0x0012, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60,
                    description="Lifetime import energy measured at the grid meter; use this for the HA energy dashboard",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_feed_to_grid_pv", "Total Energy Feed to Grid (PV)",
                    0x0090, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60,
                    description="Lifetime energy exported from PV, measured at the AC PV meter",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_charge_battery", "Total Energy Charge Battery",
                    0x0120, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60,
                    description="Lifetime energy delivered to the battery",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_discharge_battery", "Total Energy Discharge Battery",
                    0x0122, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60,
                    description="Lifetime energy drawn from the battery",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_charge_battery_from_grid", "Total Energy Charge Battery from Grid",
                    0x0124, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60,
                    description="Lifetime energy used to charge the battery from the grid",
                    group="Energy Totals"),
    ModbusSensorDef("total_energy_from_pv", "Total Energy from PV",
                    0x043E, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60,
                    description="Lifetime total PV energy generated",
                    group="Energy Totals"),

    # --- Faults & warnings ---
    ModbusSensorDef("system_fault", "System Fault",
                    0x08D4, "uint32", precision=0, scan_interval=5, enabled_by_default=True,
                    description="System-level fault bitmap; non-zero means a fault is active",
                    group="Faults & Warnings"),
    ModbusSensorDef("inverter_warning_1", "Inverter Warning 1",
                    0x0436, "uint32", precision=0, scan_interval=5,
                    description="Inverter warning bitmap, word 1 of 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("inverter_warning_2", "Inverter Warning 2",
                    0x0438, "uint32", precision=0, scan_interval=5,
                    description="Inverter warning bitmap, word 2 of 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("inverter_fault_1", "Inverter Fault 1",
                    0x043A, "uint32", precision=0, scan_interval=5,
                    description="Inverter fault bitmap, word 1 of 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("inverter_fault_2", "Inverter Fault 2",
                    0x043C, "uint32", precision=0, scan_interval=5,
                    description="Inverter fault bitmap, word 2 of 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_warning", "Battery Warning",
                    0x011C, "uint32", precision=0, scan_interval=5,
                    description="Aggregate battery warning bitmap",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_fault", "Battery Fault",
                    0x011E, "uint32", precision=0, scan_interval=5,
                    description="Aggregate battery fault bitmap",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_1_warning", "Battery 1 Warning",
                    0x013D, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 1",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_2_warning", "Battery 2 Warning",
                    0x013F, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_3_warning", "Battery 3 Warning",
                    0x0141, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 3",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_4_warning", "Battery 4 Warning",
                    0x0143, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 4",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_5_warning", "Battery 5 Warning",
                    0x0145, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 5",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_6_warning", "Battery 6 Warning",
                    0x0147, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Warning bitmap for battery module 6",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_1_fault", "Battery 1 Fault",
                    0x0131, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 1",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_2_fault", "Battery 2 Fault",
                    0x0133, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 2",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_3_fault", "Battery 3 Fault",
                    0x0135, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 3",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_4_fault", "Battery 4 Fault",
                    0x0137, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 4",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_5_fault", "Battery 5 Fault",
                    0x0139, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 5",
                    group="Faults & Warnings"),
    ModbusSensorDef("battery_6_fault", "Battery 6 Fault",
                    0x013B, "uint32", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Fault bitmap for battery module 6",
                    group="Faults & Warnings"),

    # --- Grid safety ---
    ModbusSensorDef("grid_regulation", "Grid Regulation",
                    0x1000, "int16", precision=0, scan_interval=60, enabled_by_default=False,
                    description="Active grid compliance standard or regulation profile",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l1", "Overvoltage Protection L1",
                    0x100B, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Over-voltage protection threshold, level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l1_time", "Overvoltage Protection L1 Time",
                    0x100C, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-voltage protection level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l2", "Overvoltage Protection L2",
                    0x101B, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Over-voltage protection threshold, level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l2_time", "Overvoltage Protection L2 Time",
                    0x101C, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-voltage protection level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l3", "Overvoltage Protection L3",
                    0x101D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Over-voltage protection threshold, level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ovp_l3_time", "Overvoltage Protection L3 Time",
                    0x101E, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-voltage protection level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ovp10", "Overvoltage Protection 10min",
                    0x100D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="10-minute average over-voltage protection threshold",
                    group="Grid Safety"),
    ModbusSensorDef("ovp10_time", "Overvoltage Protection 10min Time",
                    0x100E, "int16", unit="s", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for 10-minute over-voltage protection",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l1", "Undervoltage Protection L1",
                    0x100F, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Under-voltage protection threshold, level 1",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l1_time", "Undervoltage Protection L1 Time",
                    0x1010, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-voltage protection level 1",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l2", "Undervoltage Protection L2",
                    0x1011, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Under-voltage protection threshold, level 2",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l2_time", "Undervoltage Protection L2 Time",
                    0x1012, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-voltage protection level 2",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l3", "Undervoltage Protection L3",
                    0x101F, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False,
                    description="Under-voltage protection threshold, level 3",
                    group="Grid Safety"),
    ModbusSensorDef("uvp_l3_time", "Undervoltage Protection L3 Time",
                    0x1020, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-voltage protection level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l1", "Overfrequency Protection L1",
                    0x1013, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Over-frequency protection threshold, level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l1_time", "Overfrequency Protection L1 Time",
                    0x1014, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-frequency protection level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l2", "Overfrequency Protection L2",
                    0x1015, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Over-frequency protection threshold, level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l2_time", "Overfrequency Protection L2 Time",
                    0x1016, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-frequency protection level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l3", "Overfrequency Protection L3",
                    0x1021, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Over-frequency protection threshold, level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ofp_l3_time", "Overfrequency Protection L3 Time",
                    0x1022, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for over-frequency protection level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l1", "Underfrequency Protection L1",
                    0x1017, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Under-frequency protection threshold, level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l1_time", "Underfrequency Protection L1 Time",
                    0x1018, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-frequency protection level 1",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l2", "Underfrequency Protection L2",
                    0x1019, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Under-frequency protection threshold, level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l2_time", "Underfrequency Protection L2 Time",
                    0x101A, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-frequency protection level 2",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l3", "Underfrequency Protection L3",
                    0x1023, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False,
                    description="Under-frequency protection threshold, level 3",
                    group="Grid Safety"),
    ModbusSensorDef("ufp_l3_time", "Underfrequency Protection L3 Time",
                    0x1024, "int16", unit="ms", scan_interval=60, enabled_by_default=False,
                    description="Trip delay for under-frequency protection level 3",
                    group="Grid Safety"),

    # --- Battery ---
    ModbusSensorDef("soc_battery", "Battery State of Charge",
                    0x0102, "int16", unit="%", device_class="battery",
                    scale=0.1, precision=1, scan_interval=10,
                    description="Battery state of charge",
                    group="Battery"),
    ModbusSensorDef("soh_battery", "Battery State of Health",
                    0x011B, "int16", unit="%", device_class="battery",
                    scale=0.1, scan_interval=10,
                    description="Battery state of health; 100% indicates a fully healthy pack",
                    group="Battery"),
    ModbusSensorDef("battery_status", "Battery Status",
                    0x0103, "int16", state_class=None, scan_interval=60,
                    description="Battery status code reported by the BMS",
                    group="Battery"),
    ModbusSensorDef("battery_voltage", "Battery Voltage",
                    0x0100, "int16", unit="V", device_class="voltage",
                    scale=0.1, precision=2, scan_interval=60,
                    description="Battery pack terminal voltage",
                    group="Battery"),
    ModbusSensorDef("battery_current", "Battery Current",
                    0x0101, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60,
                    description="Battery pack current; positive = charging, negative = discharging",
                    group="Battery"),
    ModbusSensorDef("battery_min_cell_temp", "Battery Min Cell Temp",
                    0x010D, "uint16", unit="°C", device_class="temperature",
                    scale=0.1, precision=1, scan_interval=10,
                    description="Lowest temperature across all battery cells",
                    group="Battery"),
    ModbusSensorDef("battery_max_cell_temp", "Battery Max Cell Temp",
                    0x0110, "uint16", unit="°C", device_class="temperature",
                    scale=0.1, precision=1, scan_interval=10,
                    description="Highest temperature across all battery cells",
                    group="Battery"),
    ModbusSensorDef("battery_max_charge_current", "Battery Max Charge Current",
                    0x0111, "uint16", unit="A", device_class="current",
                    scale=0.1, precision=1, scan_interval=10,
                    description="Maximum charge current allowed by the BMS at present",
                    group="Battery"),
    ModbusSensorDef("battery_max_discharge_current", "Battery Max Discharge Current",
                    0x0112, "uint16", unit="A", device_class="current",
                    scale=0.1, precision=1, scan_interval=10,
                    description="Maximum discharge current allowed by the BMS at present",
                    group="Battery"),
    ModbusSensorDef("battery_remaining_time_raw", "Battery Remaining Time (raw)",
                    0x0127, "int16", unit="min", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="BMS estimate of time to full charge or discharge",
                    group="Battery"),
    ModbusSensorDef("battery_relay_status", "Battery Relay Status",
                    0x0104, "uint16", precision=0, scan_interval=60, enabled_by_default=False,
                    description="Battery contactor/relay state bitmap",
                    group="Battery"),
    ModbusSensorDef("battery_min_cell_voltage", "Battery Min Cell Voltage",
                    0x0107, "uint16", unit="V", device_class="voltage",
                    scale=0.001, precision=3, scan_interval=60, enabled_by_default=True,
                    description="Voltage of the lowest cell in the pack; watch for cell imbalance",
                    group="Battery"),
    ModbusSensorDef("battery_max_cell_voltage", "Battery Max Cell Voltage",
                    0x010A, "uint16", unit="V", device_class="voltage",
                    scale=0.001, precision=3, scan_interval=60, enabled_by_default=True,
                    description="Voltage of the highest cell in the pack; watch for cell imbalance",
                    group="Battery"),
    ModbusSensorDef("battery_charge_cutoff_voltage", "Battery Charge Cutoff Voltage",
                    0x0113, "uint16", unit="V", device_class="voltage",
                    scale=0.1, precision=1, scan_interval=300, enabled_by_default=False,
                    description="Pack voltage at which the BMS stops charging",
                    group="Battery"),
    ModbusSensorDef("battery_discharge_cutoff_voltage", "Battery Discharge Cutoff Voltage",
                    0x0114, "uint16", unit="V", device_class="voltage",
                    scale=0.1, precision=1, scan_interval=300, enabled_by_default=False,
                    description="Pack voltage at which the BMS stops discharging",
                    group="Battery"),
    ModbusSensorDef("battery_module_count", "Battery Module Count",
                    0x0118, "uint16", precision=0, scan_interval=300, enabled_by_default=False,
                    description="Number of battery modules in the installed pack",
                    group="Battery"),
    ModbusSensorDef("battery_capacity_kwh", "Battery Capacity",
                    0x0119, "uint16", unit="kWh", device_class="energy_storage",
                    scale=0.1, precision=1, scan_interval=300, enabled_by_default=False,
                    description="Total rated capacity of the installed battery pack",
                    group="Battery"),
    ModbusSensorDef("battery_type", "Battery Type",
                    0x011A, "uint16", precision=0, scan_interval=300, enabled_by_default=False,
                    description="Battery chemistry or model type code",
                    group="Battery"),

    # --- PV settings (read-only view) ---
    ModbusSensorDef("max_feed_to_grid", "Max Feed to Grid",
                    0x0800, "uint16", unit="%", scan_interval=5,
                    description="Maximum export power as a percentage of inverter AC capacity; also writable via number entity",
                    group="PV Settings"),
    ModbusSensorDef("pv_capacity_storage", "PV Capacity Storage",
                    0x0801, "uint32", unit="W", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="Configured DC PV capacity connected to the storage inverter",
                    group="PV Settings"),
    ModbusSensorDef("pv_capacity_grid_inverter", "PV Capacity of Grid Inverter",
                    0x0803, "uint32", unit="W", precision=0, scan_interval=60,
                    enabled_by_default=False,
                    description="Configured DC PV capacity connected to the grid-tied inverter",
                    group="PV Settings"),

    # --- Grid meter ---
    ModbusSensorDef("ct_rate_grid_meter", "CT Rate Grid Meter",
                    0x0001, "uint16", precision=0, scan_interval=60, enabled_by_default=False,
                    description="Current transformer ratio configured for the grid power meter",
                    group="Grid Meter"),
    ModbusSensorDef("ct_rate_pv_meter", "CT Rate PV Meter",
                    0x0081, "uint16", precision=0, scan_interval=60, enabled_by_default=False,
                    description="Current transformer ratio configured for the PV power meter",
                    group="Grid Meter"),

    # --- Charging time period control (read-only view) ---
    ModbusSensorDef("charging_time_period_control", "Charging Time Period Control",
                    0x084F, "int16", precision=0, scan_interval=10,
                    description="Bitmask enabling grid charging and/or discharge time windows; also writable via select entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_cutoff_soc", "Charging Cutoff SoC",
                    0x0855, "int16", unit="%", scan_interval=10,
                    description="SoC at which scheduled grid charging stops; also writable via number entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_1_start_hour", "Charging Period 1 Start Hour",
                    0x0856, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of charging window 1 start time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_1_stop_hour", "Charging Period 1 Stop Hour",
                    0x0857, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of charging window 1 stop time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_2_start_hour", "Charging Period 2 Start Hour",
                    0x0858, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of charging window 2 start time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_2_stop_hour", "Charging Period 2 Stop Hour",
                    0x0859, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of charging window 2 stop time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_1_start_minute", "Charging Period 1 Start Minute",
                    0x085E, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of charging window 1 start time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_1_stop_minute", "Charging Period 1 Stop Minute",
                    0x085F, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of charging window 1 stop time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_2_start_minute", "Charging Period 2 Start Minute",
                    0x0860, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of charging window 2 start time; also writable via time entity",
                    group="Charge Schedule"),
    ModbusSensorDef("charging_period_2_stop_minute", "Charging Period 2 Stop Minute",
                    0x0861, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of charging window 2 stop time; also writable via time entity",
                    group="Charge Schedule"),

    # --- Discharging ---
    ModbusSensorDef("discharging_cutoff_soc", "Discharging Cutoff SoC",
                    0x0850, "int16", unit="%", scan_interval=30,
                    description="SoC at which scheduled battery discharge stops; also writable via number entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_1_start_hour", "Discharging Period 1 Start Hour",
                    0x0851, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of discharge window 1 start time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_1_stop_hour", "Discharging Period 1 Stop Hour",
                    0x0852, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of discharge window 1 stop time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_2_start_hour", "Discharging Period 2 Start Hour",
                    0x0853, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of discharge window 2 start time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_2_stop_hour", "Discharging Period 2 Stop Hour",
                    0x0854, "int16", unit="h", precision=0, scan_interval=30,
                    description="Hour component of discharge window 2 stop time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_1_start_minute", "Discharging Period 1 Start Minute",
                    0x085A, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of discharge window 1 start time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_1_stop_minute", "Discharging Period 1 Stop Minute",
                    0x085B, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of discharge window 1 stop time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_2_start_minute", "Discharging Period 2 Start Minute",
                    0x085C, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of discharge window 2 start time; also writable via time entity",
                    group="Discharge Schedule"),
    ModbusSensorDef("discharging_period_2_stop_minute", "Discharging Period 2 Stop Minute",
                    0x085D, "int16", unit="min", precision=0, scan_interval=30,
                    description="Minute component of discharge window 2 stop time; also writable via time entity",
                    group="Discharge Schedule"),

    # --- Dispatch (read-only view) ---
    ModbusSensorDef("dispatch_start", "Dispatch Start",
                    0x0880, "int16", precision=0, scan_interval=5,
                    description="Dispatch active flag; 1 = dispatch running, 0 = idle",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_active_power", "Dispatch Active Power",
                    0x0881, "int32", unit="W", offset=-32000, precision=0, scan_interval=5,
                    description="Active power setpoint in the current dispatch command; positive = discharge/export, negative = charge/import (offset-corrected from the raw 32000-bias encoding)",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_reactive_power", "Dispatch Reactive Power",
                    0x0883, "int32", unit="W", offset=-32000, precision=0, scan_interval=5,
                    description="Reactive power setpoint in the current dispatch command (offset-corrected from raw 32000-bias encoding)",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_mode", "Dispatch Mode",
                    0x0885, "int16", precision=0, scan_interval=5,
                    description="Control mode for the active dispatch command",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_soc", "Dispatch SoC",
                    0x0886, "int16", unit="%", scale=0.392, precision=0, scan_interval=5,
                    description="SoC target in the current dispatch command, converted from raw to percent",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_time", "Dispatch Time",
                    0x0887, "uint32", state_class=None, scan_interval=5,
                    description="Time register for the current dispatch command; raw 32-bit value in seconds",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_energy_flow_direction", "Dispatch Energy Flow Direction",
                    0x0889, "uint16", precision=0, scan_interval=5, state_class=None,
                    enabled_by_default=True,
                    description="Energy flow direction code reported by the dispatch subsystem",
                    group="Dispatch State"),
    ModbusSensorDef("dispatch_pv_switch", "Dispatch PV Switch",
                    0x088A, "uint16", precision=0, scan_interval=5, enabled_by_default=True,
                    description="PV coupling flag in the dispatch control block",
                    group="Dispatch State"),
    ModbusSensorDef("freq_dispatch_flag", "Freq Dispatch Flag",
                    0x088F, "uint16", precision=0, scan_interval=5, enabled_by_default=True,
                    description="Indicates whether frequency-responsive dispatch is enabled",
                    group="Dispatch State"),
    ModbusSensorDef("freq_dispatch_power", "Freq Dispatch Power",
                    0x0890, "int16", unit="W", precision=0, scan_interval=5, enabled_by_default=False,
                    description="Power setpoint for frequency-responsive dispatch events",
                    group="Dispatch State"),
    ModbusSensorDef("freq_dispatch_frequency", "Freq Dispatch Frequency",
                    0x0891, "uint16", unit="Hz", scale=0.01, precision=2,
                    scan_interval=5, enabled_by_default=False,
                    description="Frequency threshold that triggers frequency-responsive dispatch",
                    group="Dispatch State"),
]

# ---------------------------------------------------------------------------
# NUMBER REGISTERS (writable sliders)
# ---------------------------------------------------------------------------
NUMBER_REGISTERS: list[ModbusNumberDef] = [
    ModbusNumberDef("charging_cutoff_soc", "Charging Cutoff SoC",
                    0x0855, min_value=10, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="SoC at which scheduled grid charging stops; live value is read back from the register on each poll"),
    ModbusNumberDef("discharging_cutoff_soc", "Discharging Cutoff SoC",
                    0x0850, min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="SoC at which scheduled battery discharge stops; live value is read back from the register on each poll"),
    ModbusNumberDef("max_feed_to_grid", "Max Feed to Grid",
                    0x0800, min_value=0, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Maximum export power as a percentage of inverter AC capacity; live value is read back from the register on each poll"),
    # Dispatch-only params: address=None so no code path can write them directly.
    # Values are read by switch.py and assembled into the 9-register dispatch sequence.
    ModbusNumberDef("force_charging_cutoff_soc", "Force Charging Stop at SoC",
                    address=None,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Force Charging stops when battery reaches this SoC (dispatch parameter, not written directly to a register)"),
    ModbusNumberDef("force_charging_duration", "Force Charging Duration",
                    address=None,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline",
                    description="Maximum time Force Charging runs before auto-stopping (dispatch parameter)"),
    ModbusNumberDef("force_charging_power", "Force Charging Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash", ac_limit_scaled=True,
                    description="Target charge power for Force Charging, capped to inverter AC limit (dispatch parameter)"),
    ModbusNumberDef("force_discharging_cutoff_soc", "Force Discharging Stop at SoC",
                    address=None,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Force Discharging stops when battery falls to this SoC (dispatch parameter)"),
    ModbusNumberDef("force_discharging_duration", "Force Discharging Duration",
                    address=None,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline",
                    description="Maximum time Force Discharging runs before auto-stopping (dispatch parameter)"),
    ModbusNumberDef("force_discharging_power", "Force Discharging Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash", ac_limit_scaled=True,
                    description="Target discharge power for Force Discharging, capped to inverter AC limit (dispatch parameter)"),
    ModbusNumberDef("force_export_cutoff_soc", "Force Export Stop at SoC",
                    address=None,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Force Export stops when battery falls to this SoC (dispatch parameter)"),
    ModbusNumberDef("force_export_duration", "Force Export Duration",
                    address=None,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline",
                    description="Maximum time Force Export runs before auto-stopping (dispatch parameter)"),
    ModbusNumberDef("force_export_power", "Force Export Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash", ac_limit_scaled=True,
                    description="Target grid export level for Force Export; the integration adds house load and subtracts PV to derive the battery dispatch value (dispatch parameter)"),
    ModbusNumberDef("dispatch_cutoff_soc", "Dispatch Stop at SoC",
                    address=None,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Generic Dispatch stops when battery reaches this SoC in mode 2 (SoC Control) (dispatch parameter)"),
    ModbusNumberDef("dispatch_duration", "Dispatch Duration",
                    address=None,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline",
                    description="Maximum time Generic Dispatch runs before auto-stopping (dispatch parameter)"),
    ModbusNumberDef("dispatch_power", "Dispatch Power",
                    address=None,
                    min_value=-20, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash", ac_limit_scaled=True, default_value=0,
                    description="Power setpoint for Generic Dispatch; positive = discharge/export, negative = charge/import (dispatch parameter)"),
    ModbusNumberDef("force_import_cutoff_soc", "Force Import Stop at SoC",
                    address=None,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline",
                    description="Force Import stops when battery reaches this SoC (dispatch parameter)"),
    ModbusNumberDef("force_import_duration", "Force Import Duration",
                    address=None,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline",
                    description="Maximum time Force Import runs before auto-stopping (dispatch parameter)"),
    ModbusNumberDef("force_import_power", "Force Import Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash", ac_limit_scaled=True,
                    description="Target grid import level for Force Import; the integration subtracts PV and adds house load to derive the battery charge value (dispatch parameter)"),
    # Charging/discharging period times are handled by the time platform (time.py)
    # using ModbusTimeDef entries in TIME_REGISTERS below.
]

# ---------------------------------------------------------------------------
# SELECT REGISTERS (writable dropdowns)
# ---------------------------------------------------------------------------
SELECT_REGISTERS: list[ModbusSelectDef] = [
    ModbusSelectDef(
        "charging_discharging_settings",
        "Charging / Discharging Settings",
        address=0x084F,
        options=[
            "Disable",
            "Enable Grid Charging Battery",
            "Enable Battery Discharge Time Control",
            "Enable Grid Charging Battery & Battery Discharge Time Control",
        ],
        values=[0, 1, 2, 3],
        icon="mdi:battery-charging",
        sensor_key="charging_time_period_control",
        description="Enables or disables the scheduled grid charging and discharge time windows",
    ),
    ModbusSelectDef(
        "dispatch_mode",
        "Dispatch Mode",
        address=0x0885,
        options=[
            "Battery only Charges from PV (1)",
            "State of Charge Control (2)",
            "Load Following (3)",
            "Maximise Output (4)",
            "Normal Mode (5)",
            "Optimise Consumption (6)",
            "Maximise Consumption (7)",
            "No Battery Charge (19)",
        ],
        values=[1, 2, 3, 4, 5, 6, 7, 19],
        icon="mdi:battery-arrow-up-outline",
        sensor_key="dispatch_mode",
        description="Selects the control algorithm used when a dispatch switch is active",
    ),
    ModbusSelectDef(
        "inverter_ac_limit",
        "Inverter AC Limit",
        address=None,  # stored in config entry, used in excess export calculation
        options=["3 kW", "4 kW", "4.6 kW", "5 kW", "6 kW",
                 "8 kW", "10 kW", "12 kW", "15 kW", "20 kW"],
        values=[3000, 4000, 4600, 5000, 6000, 8000, 10000, 12000, 15000, 20000],
        icon="mdi:transmission-tower",
        description="Inverter AC output rating; used to calculate battery power needed for Force Export and Excess Export",
    ),
]

# ---------------------------------------------------------------------------
# TIME REGISTERS (charging/discharging period start & stop times)
# Each entry writes hour + minute as separate registers but presents as hh:mm.
# The underlying sensor reads (hour_key / minute_key) are in SENSOR_REGISTERS.
# ---------------------------------------------------------------------------
TIME_REGISTERS: list[ModbusTimeDef] = [
    ModbusTimeDef("charging_period_1_start", "Charging Period 1 Start Time",
                  0x0856, 0x085E, "mdi:clock-start",
                  description="Start time of scheduled grid charging window 1 (writes hour and minute as two separate registers)"),
    ModbusTimeDef("charging_period_1_stop", "Charging Period 1 Stop Time",
                  0x0857, 0x085F, "mdi:clock-end",
                  description="Stop time of scheduled grid charging window 1"),
    ModbusTimeDef("charging_period_2_start", "Charging Period 2 Start Time",
                  0x0858, 0x0860, "mdi:clock-start",
                  description="Start time of scheduled grid charging window 2"),
    ModbusTimeDef("charging_period_2_stop", "Charging Period 2 Stop Time",
                  0x0859, 0x0861, "mdi:clock-end",
                  description="Stop time of scheduled grid charging window 2"),
    ModbusTimeDef("discharging_period_1_start", "Discharging Period 1 Start Time",
                  0x0851, 0x085A, "mdi:clock-start",
                  description="Start time of scheduled battery discharge window 1"),
    ModbusTimeDef("discharging_period_1_stop", "Discharging Period 1 Stop Time",
                  0x0852, 0x085B, "mdi:clock-end",
                  description="Stop time of scheduled battery discharge window 1"),
    ModbusTimeDef("discharging_period_2_start", "Discharging Period 2 Start Time",
                  0x0853, 0x085C, "mdi:clock-start",
                  description="Start time of scheduled battery discharge window 2"),
    ModbusTimeDef("discharging_period_2_stop", "Discharging Period 2 Stop Time",
                  0x0854, 0x085D, "mdi:clock-end",
                  description="Stop time of scheduled battery discharge window 2"),
]

# ---------------------------------------------------------------------------
# SWITCH and BUTTON descriptions
# Used by scripts/generate_register_docs.py to build the register map document.
# Tuple format: (display_name, description)
# ---------------------------------------------------------------------------
SWITCH_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "force_charging": (
        "Force Charging",
        "Charges the battery at the configured power level; stops at the cutoff SoC, after the duration, "
        "or when battery power drops to near zero (unless Force Charging Hold is on)",
    ),
    "force_charging_hold": (
        "Force Charging Hold",
        "Prevents Force Charging from auto-stopping when battery power nears zero; useful when the inverter "
        "reduces charging before reaching the SoC target",
    ),
    "force_discharging": (
        "Force Discharging",
        "Discharges the battery at the configured power level; stops at the cutoff SoC or after the duration",
    ),
    "force_discharging_hold": (
        "Force Discharging Hold",
        "Prevents Force Discharging from auto-stopping when battery power nears zero",
    ),
    "force_export": (
        "Force Export",
        "Exports power to the grid at the configured level; dynamically adjusts battery dispatch to account "
        "for live house load and PV production, refreshing every 25 seconds",
    ),
    "force_export_hold": (
        "Force Export Hold",
        "Prevents Force Export from auto-stopping when battery power nears zero",
    ),
    "force_import": (
        "Force Import",
        "Charges the battery using grid import at the configured level; accounts for live house load and PV, "
        "refreshing every 25 seconds",
    ),
    "force_import_hold": (
        "Force Import Hold",
        "Prevents Force Import from auto-stopping when battery power nears zero",
    ),
    "dispatch": (
        "Dispatch",
        "Sends a generic dispatch command with the configured power, mode, SoC target, and duration",
    ),
    "excess_export": (
        "Excess Export",
        "Exports battery power equal to DC PV clipping (DC PV output minus inverter AC capacity); "
        "auto-pauses when importing from grid and resumes when conditions allow",
    ),
}

BUTTON_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "dispatch_reset": (
        "Dispatch Reset",
        "Writes the dispatch stop command; returns the inverter to its configured scheduled operating mode",
    ),
    "synchronise_date_time": (
        "Synchronise Date & Time",
        "Sets the inverter real-time clock to match the current Home Assistant system time",
    ),
    "sync_dispatch_state": (
        "Sync Dispatch State",
        "Reads live dispatch registers and corrects HA switch states to match; useful after a HA restart "
        "if a dispatch was active when HA stopped",
    ),
    "restart_pcs": (
        "Restart PCS",
        "Restarts the Power Conversion System by writing code 7 to the reset register; use with caution",
    ),
    "restart_ems": (
        "Restart EMS",
        "Restarts the Energy Management System by writing code 8 to the reset register; use with caution",
    ),
    "reset_energy_totals": (
        "Reset Energy Totals",
        "Clears all lifetime energy counters by writing code 1 to the reset register; this is irreversible",
    ),
}

# ---------------------------------------------------------------------------
# Daily energy sensor definitions
# Each tuple: (key, source_key_in_coordinator_data, ac_power_key_or_None)
# source_key must be a key in SENSOR_REGISTERS with state_class="total_increasing"
# ac_power_key: if set, Riemann-integrates that live power register and adds
# the accumulated kWh to the DC register delta (used for AC-coupled PV)
# ---------------------------------------------------------------------------
DAILY_ENERGY_SENSORS: list[tuple[str, str, str | None]] = [
    ("today_energy_feed_to_grid",       "total_energy_feed_to_grid_meter",           None),
    ("today_energy_from_grid",          "total_energy_consumption_from_grid_meter",  None),
    ("today_pv_generation",             "total_energy_from_pv",                      "active_power_pv_meter"),
    ("today_battery_charged",           "total_energy_charge_battery",               None),
    ("today_battery_discharged",        "total_energy_discharge_battery",            None),
    ("today_battery_charged_from_grid", "total_energy_charge_battery_from_grid",     None),
]

# ---------------------------------------------------------------------------
# B3 / B3PLUS model scale overrides
# Source: integration_alpha_ess.yaml v10.5 (comments "X for SMILE-B3/SMILE-B3-PLUS")
# B3 and B3PLUS share identical scales, so a single "b3" variant covers both.
#
# | key                    | std scale | B3 scale |
# |------------------------|-----------|----------|
# | inverter_temperature   |   0.1     |   0.01   |
# | voltage_phase_a_grid   |   1.0     |   0.1    |
# | voltage_phase_b_grid   |   1.0     |   0.1    |
# | voltage_phase_c_grid   |   1.0     |   0.1    |
# | power_inverter_l1      |   1.0     |   0.1    |
# | power_inverter_l2      |   1.0     |   0.1    |
# | power_inverter_l3      |   1.0     |   0.1    |
# | power_inverter         |   1.0     |   0.1    |
# | backup_power_inverter_l1|  1.0     |   0.1    |
# | backup_power_inverter_l2|  1.0     |   0.1    |
# | backup_power_inverter_l3|  1.0     |   0.1    |
# | backup_power_inverter  |   1.0     |   0.1    |
# ---------------------------------------------------------------------------
B3_SCALE_OVERRIDES: dict[str, float] = {
    "inverter_temperature":    0.01,
    "voltage_phase_a_grid":    0.1,
    "voltage_phase_b_grid":    0.1,
    "voltage_phase_c_grid":    0.1,
    "power_inverter_l1":       0.1,
    "power_inverter_l2":       0.1,
    "power_inverter_l3":       0.1,
    "power_inverter":          0.1,
    "backup_power_inverter_l1": 0.1,
    "backup_power_inverter_l2": 0.1,
    "backup_power_inverter_l3": 0.1,
    "backup_power_inverter":   0.1,
}

# ---------------------------------------------------------------------------
# Dispatch register base address (used in switch/button write sequences)
# ---------------------------------------------------------------------------
DISPATCH_START_ADDR = 0x0880

# Dispatch mode values
DISPATCH_MODE_SOC_CONTROL = 2
DISPATCH_SOC_SCALE = 0.392  # %/bit

# Trailing dispatch-block registers (offsets 9 and 10 past DISPATCH_START_ADDR).
# Flow Direction (0x0889) is hardcoded to 255 in every dispatch write.
# PV Switch (0x088A) is writable: 1 = PV on, 2 = PV off. Force modes write 0
# (leave unchanged). Confirmed on real DC-coupled hardware: the switch only takes
# effect during an active dispatch, and the inverter restores PV when it ends.
DISPATCH_FLOW_DIRECTION = 255
DISPATCH_PV_SWITCH_ADDR = 0x088A
DISPATCH_PV_ON = 1
DISPATCH_PV_OFF = 2
DISPATCH_PV_UNCHANGED = 0

# Charging/discharging time period control register
CHARGING_TIME_PERIOD_ADDR = 0x084F

# Reset/restart register
RESET_MODE_ADDR = 0x1100
