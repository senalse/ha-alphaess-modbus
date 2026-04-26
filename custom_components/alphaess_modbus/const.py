from __future__ import annotations
from dataclasses import dataclass, field

DOMAIN = "alphaess_modbus"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 85
DEFAULT_SCAN_INTERVAL = 30
MODBUS_HUB = "alphaess_modbus_hub"

PLATFORMS = ["sensor", "number", "select", "switch", "button", "time"]

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


@dataclass
class ModbusSelectDef:
    key: str
    name: str
    address: int
    options: list[str] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    icon: str | None = None


@dataclass
class ModbusTimeDef:
    key: str
    name: str
    hour_address: int
    minute_address: int
    icon: str = "mdi:clock-outline"


# ---------------------------------------------------------------------------
# SENSOR REGISTERS
# Source: integration_alpha_ess.yaml v10.4
# ---------------------------------------------------------------------------
SENSOR_REGISTERS: list[ModbusSensorDef] = [
    # --- Measurements: system ---
    ModbusSensorDef("inverter_grid_frequency", "Grid Frequency",
                    0x041C, "int16", unit="Hz", device_class="frequency",
                    scale=0.01, precision=2, scan_interval=30),
    ModbusSensorDef("inverter_temperature", "Inverter Temperature",
                    0x0435, "int16", unit="°C", device_class="temperature",
                    scale=0.1, precision=0, scan_interval=60),
    ModbusSensorDef("inverter_work_mode", "Inverter Work Mode",
                    0x0440, "int16", scan_interval=5),
    ModbusSensorDef("inverter_sn", "Inverter Serial Number",
                    0x064A, "string", count=15, scan_interval=60,
                    state_class=None),
    ModbusSensorDef("bms_version", "BMS Version",
                    0x0115, "int16", scan_interval=60),
    ModbusSensorDef("lmu_version", "LMU Version",
                    0x0116, "int16", scan_interval=60),
    ModbusSensorDef("iso_version", "ISO Version",
                    0x0117, "int16", scan_interval=60),
    ModbusSensorDef("inverter_version", "Inverter Version",
                    0x0640, "string", count=5, scan_interval=60,
                    state_class=None),
    ModbusSensorDef("inverter_arm_version", "Inverter ARM Version",
                    0x0645, "string", count=5, scan_interval=60,
                    state_class=None),
    ModbusSensorDef("ems_version_high", "EMS Version High",
                    0x074B, "int16", scan_interval=60),
    ModbusSensorDef("ems_version_middle", "EMS Version Middle",
                    0x074C, "int16", scan_interval=60),
    ModbusSensorDef("ems_version_low", "EMS Version Low",
                    0x074D, "int16", scan_interval=60),
    ModbusSensorDef("ems_version_low_suffix", "EMS Version Low Suffix",
                    0x074F, "string", count=3, scan_interval=60,
                    state_class=None),

    # --- System time ---
    ModbusSensorDef("system_time_yymm", "System Time YYMM",
                    0x0740, "int16", scan_interval=5,
                    enabled_by_default=False),
    ModbusSensorDef("system_time_ddhh", "System Time DDHH",
                    0x0741, "int16", scan_interval=5,
                    enabled_by_default=False),
    ModbusSensorDef("system_time_mmss", "System Time MMSS",
                    0x0742, "int16", scan_interval=5,
                    enabled_by_default=False),

    # --- Network ---
    ModbusSensorDef("modbus_baud_rate", "Modbus Baud Rate",
                    0x0810, "uint16", scan_interval=60,
                    enabled_by_default=False),
    ModbusSensorDef("ip_method", "IP Method",
                    0x0808, "uint16", scan_interval=60,
                    enabled_by_default=False),
    ModbusSensorDef("local_ip", "Local IP (raw)",
                    0x0809, "uint32", scan_interval=60,
                    enabled_by_default=False),
    ModbusSensorDef("subnet_mask", "Subnet Mask (raw)",
                    0x080B, "uint32", scan_interval=60,
                    enabled_by_default=False),
    ModbusSensorDef("gateway", "Gateway (raw)",
                    0x080D, "uint32", scan_interval=60,
                    enabled_by_default=False),

    # --- Power: grid ---
    ModbusSensorDef("power_grid", "Grid Power",
                    0x0021, "int32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("power_phase_a_grid", "Grid Power Phase A",
                    0x001B, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("power_phase_b_grid", "Grid Power Phase B",
                    0x001D, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("power_phase_c_grid", "Grid Power Phase C",
                    0x001F, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("voltage_phase_a_grid", "Grid Voltage Phase A",
                    0x0014, "int16", unit="V", device_class="voltage",
                    scan_interval=5),
    ModbusSensorDef("voltage_phase_b_grid", "Grid Voltage Phase B",
                    0x0015, "int16", unit="V", device_class="voltage",
                    scan_interval=5),
    ModbusSensorDef("voltage_phase_c_grid", "Grid Voltage Phase C",
                    0x0016, "int16", unit="V", device_class="voltage",
                    scan_interval=5),

    # --- Power: battery ---
    ModbusSensorDef("power_battery", "Battery Power",
                    0x0126, "int16", unit="W", device_class="power",
                    scan_interval=1),

    # --- Power: inverter ---
    ModbusSensorDef("power_inverter_l1", "Inverter Power L1",
                    0x0406, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("power_inverter_l2", "Inverter Power L2",
                    0x0408, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("power_inverter_l3", "Inverter Power L3",
                    0x040A, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("power_inverter", "Inverter Power",
                    0x040C, "int32", unit="W", device_class="power",
                    scan_interval=5),
    ModbusSensorDef("backup_power_inverter_l1", "Backup Inverter Power L1",
                    0x0414, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("backup_power_inverter_l2", "Backup Inverter Power L2",
                    0x0416, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("backup_power_inverter_l3", "Backup Inverter Power L3",
                    0x0418, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("backup_power_inverter", "Backup Inverter Power",
                    0x041A, "int32", unit="W", device_class="power",
                    scan_interval=5, enabled_by_default=False),

    # --- Power: PV ---
    ModbusSensorDef("active_power_pv_meter", "Active Power PV Meter",
                    0x00A1, "int32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("pv1_power", "PV String 1 Power",
                    0x041F, "uint32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("pv1_voltage", "PV String 1 Voltage",
                    0x041D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60),
    ModbusSensorDef("pv1_current", "PV String 1 Current",
                    0x041E, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("pv2_power", "PV String 2 Power",
                    0x0423, "uint32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("pv2_voltage", "PV String 2 Voltage",
                    0x0421, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60),
    ModbusSensorDef("pv2_current", "PV String 2 Current",
                    0x0422, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("pv3_power", "PV String 3 Power",
                    0x0427, "uint32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("pv3_voltage", "PV String 3 Voltage",
                    0x0425, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60),
    ModbusSensorDef("pv3_current", "PV String 3 Current",
                    0x0426, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("pv4_power", "PV String 4 Power",
                    0x042B, "uint32", unit="W", device_class="power",
                    scan_interval=1),
    ModbusSensorDef("pv4_voltage", "PV String 4 Voltage",
                    0x0429, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60),
    ModbusSensorDef("pv4_current", "PV String 4 Current",
                    0x042A, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60),

    # --- Energy totals ---
    ModbusSensorDef("total_energy_feed_to_grid_meter", "Total Energy Feed to Grid (Meter)",
                    0x0010, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_consumption_from_grid_meter", "Total Energy Consumption from Grid (Meter)",
                    0x0012, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_feed_to_grid_pv", "Total Energy Feed to Grid (PV)",
                    0x0090, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.01, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_charge_battery", "Total Energy Charge Battery",
                    0x0120, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_discharge_battery", "Total Energy Discharge Battery",
                    0x0122, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_charge_battery_from_grid", "Total Energy Charge Battery from Grid",
                    0x0124, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("total_energy_from_pv", "Total Energy from PV",
                    0x043E, "uint32", unit="kWh", device_class="energy",
                    state_class="total_increasing", scale=0.1, precision=2, scan_interval=60),

    # --- Faults & warnings ---
    ModbusSensorDef("system_fault", "System Fault",
                    0x08D4, "uint32", scan_interval=5, enabled_by_default=True),
    ModbusSensorDef("inverter_warning_1", "Inverter Warning 1",
                    0x0436, "uint32", scan_interval=5),
    ModbusSensorDef("inverter_warning_2", "Inverter Warning 2",
                    0x0438, "uint32", scan_interval=5),
    ModbusSensorDef("inverter_fault_1", "Inverter Fault 1",
                    0x043A, "uint32", scan_interval=5),
    ModbusSensorDef("inverter_fault_2", "Inverter Fault 2",
                    0x043C, "uint32", scan_interval=5),
    ModbusSensorDef("battery_warning", "Battery Warning",
                    0x011C, "uint32", scan_interval=5),
    ModbusSensorDef("battery_fault", "Battery Fault",
                    0x011E, "uint32", scan_interval=5),
    ModbusSensorDef("battery_1_warning", "Battery 1 Warning",
                    0x013D, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_2_warning", "Battery 2 Warning",
                    0x013F, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_3_warning", "Battery 3 Warning",
                    0x0141, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_4_warning", "Battery 4 Warning",
                    0x0143, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_5_warning", "Battery 5 Warning",
                    0x0145, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_6_warning", "Battery 6 Warning",
                    0x0147, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_1_fault", "Battery 1 Fault",
                    0x0131, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_2_fault", "Battery 2 Fault",
                    0x0133, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_3_fault", "Battery 3 Fault",
                    0x0135, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_4_fault", "Battery 4 Fault",
                    0x0137, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_5_fault", "Battery 5 Fault",
                    0x0139, "uint32", scan_interval=5, enabled_by_default=False),
    ModbusSensorDef("battery_6_fault", "Battery 6 Fault",
                    0x013B, "uint32", scan_interval=5, enabled_by_default=False),

    # --- Grid safety ---
    ModbusSensorDef("grid_regulation", "Grid Regulation",
                    0x1000, "int16", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l1", "Overvoltage Protection L1",
                    0x100B, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l1_time", "Overvoltage Protection L1 Time",
                    0x100C, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l2", "Overvoltage Protection L2",
                    0x101B, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l2_time", "Overvoltage Protection L2 Time",
                    0x101C, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l3", "Overvoltage Protection L3",
                    0x101D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp_l3_time", "Overvoltage Protection L3 Time",
                    0x101E, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp10", "Overvoltage Protection 10min",
                    0x100D, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ovp10_time", "Overvoltage Protection 10min Time",
                    0x100E, "int16", unit="s", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l1", "Undervoltage Protection L1",
                    0x100F, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l1_time", "Undervoltage Protection L1 Time",
                    0x1010, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l2", "Undervoltage Protection L2",
                    0x1011, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l2_time", "Undervoltage Protection L2 Time",
                    0x1012, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l3", "Undervoltage Protection L3",
                    0x101F, "int16", unit="V", device_class="voltage",
                    scale=0.1, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("uvp_l3_time", "Undervoltage Protection L3 Time",
                    0x1020, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l1", "Overfrequency Protection L1",
                    0x1013, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l1_time", "Overfrequency Protection L1 Time",
                    0x1014, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l2", "Overfrequency Protection L2",
                    0x1015, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l2_time", "Overfrequency Protection L2 Time",
                    0x1016, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l3", "Overfrequency Protection L3",
                    0x1021, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ofp_l3_time", "Overfrequency Protection L3 Time",
                    0x1022, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l1", "Underfrequency Protection L1",
                    0x1017, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l1_time", "Underfrequency Protection L1 Time",
                    0x1018, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l2", "Underfrequency Protection L2",
                    0x1019, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l2_time", "Underfrequency Protection L2 Time",
                    0x101A, "int16", unit="ms", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l3", "Underfrequency Protection L3",
                    0x1023, "int16", unit="Hz", scale=0.01, scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ufp_l3_time", "Underfrequency Protection L3 Time",
                    0x1024, "int16", unit="ms", scan_interval=60, enabled_by_default=False),

    # --- Battery ---
    ModbusSensorDef("soc_battery", "Battery State of Charge",
                    0x0102, "int16", unit="%", device_class="battery",
                    scale=0.1, precision=1, scan_interval=10),
    ModbusSensorDef("soh_battery", "Battery State of Health",
                    0x011B, "int16", unit="%", device_class="battery",
                    scale=0.1, scan_interval=10),
    ModbusSensorDef("battery_status", "Battery Status",
                    0x0103, "int16", scan_interval=60),
    ModbusSensorDef("battery_voltage", "Battery Voltage",
                    0x0100, "int16", unit="V", device_class="voltage",
                    scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("battery_current", "Battery Current",
                    0x0101, "int16", unit="A", device_class="current",
                    scale=0.1, precision=2, scan_interval=60),
    ModbusSensorDef("battery_min_cell_temp", "Battery Min Cell Temp",
                    0x010D, "uint16", unit="°C", device_class="temperature",
                    scale=0.1, precision=1, scan_interval=10),
    ModbusSensorDef("battery_max_cell_temp", "Battery Max Cell Temp",
                    0x0110, "uint16", unit="°C", device_class="temperature",
                    scale=0.1, precision=1, scan_interval=10),
    ModbusSensorDef("battery_max_charge_current", "Battery Max Charge Current",
                    0x0111, "uint16", unit="A", device_class="current",
                    scale=0.1, precision=1, scan_interval=10),
    ModbusSensorDef("battery_max_discharge_current", "Battery Max Discharge Current",
                    0x0112, "uint16", unit="A", device_class="current",
                    scale=0.1, precision=1, scan_interval=10),
    ModbusSensorDef("battery_remaining_time", "Battery Remaining Time",
                    0x0127, "int16", unit="min", scan_interval=60),

    # --- PV settings (read-only view) ---
    ModbusSensorDef("max_feed_to_grid", "Max Feed to Grid",
                    0x0800, "uint16", unit="%", scan_interval=5),
    ModbusSensorDef("pv_capacity_storage", "PV Capacity Storage",
                    0x0801, "uint32", unit="W", scan_interval=60,
                    enabled_by_default=False),
    ModbusSensorDef("pv_capacity_grid_inverter", "PV Capacity of Grid Inverter",
                    0x0803, "uint32", unit="W", scan_interval=60,
                    enabled_by_default=False),

    # --- Grid meter ---
    ModbusSensorDef("ct_rate_grid_meter", "CT Rate Grid Meter",
                    0x0001, "uint16", scan_interval=60, enabled_by_default=False),
    ModbusSensorDef("ct_rate_pv_meter", "CT Rate PV Meter",
                    0x0081, "uint16", scan_interval=60, enabled_by_default=False),

    # --- Charging time period control (read-only view) ---
    ModbusSensorDef("charging_time_period_control", "Charging Time Period Control",
                    0x084F, "int16", scan_interval=10),
    ModbusSensorDef("charging_cutoff_soc", "Charging Cutoff SoC",
                    0x0855, "int16", unit="%", scan_interval=10),
    ModbusSensorDef("charging_period_1_start_hour", "Charging Period 1 Start Hour",
                    0x0856, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("charging_period_1_stop_hour", "Charging Period 1 Stop Hour",
                    0x0857, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("charging_period_2_start_hour", "Charging Period 2 Start Hour",
                    0x0858, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("charging_period_2_stop_hour", "Charging Period 2 Stop Hour",
                    0x0859, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("charging_period_1_start_minute", "Charging Period 1 Start Minute",
                    0x085E, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("charging_period_1_stop_minute", "Charging Period 1 Stop Minute",
                    0x085F, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("charging_period_2_start_minute", "Charging Period 2 Start Minute",
                    0x0860, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("charging_period_2_stop_minute", "Charging Period 2 Stop Minute",
                    0x0861, "int16", unit="min", scan_interval=30),

    # --- Discharging ---
    ModbusSensorDef("discharging_cutoff_soc", "Discharging Cutoff SoC",
                    0x0850, "int16", unit="%", scan_interval=30),
    ModbusSensorDef("discharging_period_1_start_hour", "Discharging Period 1 Start Hour",
                    0x0851, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("discharging_period_1_stop_hour", "Discharging Period 1 Stop Hour",
                    0x0852, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("discharging_period_2_start_hour", "Discharging Period 2 Start Hour",
                    0x0853, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("discharging_period_2_stop_hour", "Discharging Period 2 Stop Hour",
                    0x0854, "int16", unit="h", scan_interval=30),
    ModbusSensorDef("discharging_period_1_start_minute", "Discharging Period 1 Start Minute",
                    0x085A, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("discharging_period_1_stop_minute", "Discharging Period 1 Stop Minute",
                    0x085B, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("discharging_period_2_start_minute", "Discharging Period 2 Start Minute",
                    0x085C, "int16", unit="min", scan_interval=30),
    ModbusSensorDef("discharging_period_2_stop_minute", "Discharging Period 2 Stop Minute",
                    0x085D, "int16", unit="min", scan_interval=30),

    # --- Dispatch (read-only view) ---
    ModbusSensorDef("dispatch_start", "Dispatch Start",
                    0x0880, "int16", scan_interval=5),
    ModbusSensorDef("dispatch_active_power", "Dispatch Active Power",
                    0x0881, "int32", unit="W", offset=-32000, scan_interval=5),
    ModbusSensorDef("dispatch_reactive_power", "Dispatch Reactive Power",
                    0x0883, "int32", unit="W", offset=-32000, scan_interval=5),
    ModbusSensorDef("dispatch_mode", "Dispatch Mode",
                    0x0885, "int16", scan_interval=5),
    ModbusSensorDef("dispatch_soc", "Dispatch SoC",
                    0x0886, "int16", unit="%", scale=0.392, scan_interval=5),
    ModbusSensorDef("dispatch_time", "Dispatch Time",
                    0x0887, "uint32", unit="s", scan_interval=5),
]

# ---------------------------------------------------------------------------
# NUMBER REGISTERS (writable sliders)
# ---------------------------------------------------------------------------
NUMBER_REGISTERS: list[ModbusNumberDef] = [
    ModbusNumberDef("charging_cutoff_soc", "Charging Cutoff SoC",
                    0x0855, min_value=10, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("discharging_cutoff_soc", "Discharging Cutoff SoC",
                    0x0850, min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("max_feed_to_grid", "Max Feed to Grid",
                    0x0800, min_value=0, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("force_charging_cutoff_soc", "Force Charging Cutoff SoC",
                    address=0x0886,  # written via dispatch sequence, not direct register
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("force_charging_duration", "Force Charging Duration",
                    address=0x0887,  # written via dispatch sequence
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline"),
    ModbusNumberDef("force_charging_power", "Force Charging Power",
                    address=0x0881,  # written via dispatch sequence
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash"),
    ModbusNumberDef("force_discharging_cutoff_soc", "Force Discharging Cutoff SoC",
                    address=0x0886,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("force_discharging_duration", "Force Discharging Duration",
                    address=0x0887,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline"),
    ModbusNumberDef("force_discharging_power", "Force Discharging Power",
                    address=0x0881,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash"),
    ModbusNumberDef("force_export_cutoff_soc", "Force Export Cutoff SoC",
                    address=0x0886,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("force_export_duration", "Force Export Duration",
                    address=0x0887,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline"),
    ModbusNumberDef("force_export_power", "Force Export Power",
                    address=0x0881,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash"),
    ModbusNumberDef("dispatch_cutoff_soc", "Dispatch Cutoff SoC",
                    address=0x0886,
                    min_value=4, max_value=100, step=1, unit="%",
                    icon="mdi:percent-box-outline"),
    ModbusNumberDef("dispatch_duration", "Dispatch Duration",
                    address=0x0887,
                    min_value=0, max_value=480, step=5, unit="min",
                    icon="mdi:clock-time-eight-outline"),
    ModbusNumberDef("dispatch_power", "Dispatch Power",
                    address=0x0881,
                    min_value=-20, max_value=20, step=0.1, unit="kW",
                    icon="mdi:flash"),

    # Smart export / smart charge params (dispatch-only, no direct register write)
    ModbusNumberDef("max_export_power", "Max Export Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:transmission-tower-export"),
    ModbusNumberDef("max_import_power", "Max Import Power",
                    address=None,
                    min_value=0, max_value=20, step=0.1, unit="kW",
                    icon="mdi:transmission-tower-import"),

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
    ),
    ModbusSelectDef(
        "inverter_ac_limit",
        "Inverter AC Limit",
        address=None,  # stored in config entry, used in excess export calculation
        options=["3 kW", "4 kW", "4.6 kW", "5 kW", "6 kW",
                 "8 kW", "10 kW", "12 kW", "15 kW", "20 kW"],
        values=[3000, 4000, 4600, 5000, 6000, 8000, 10000, 12000, 15000, 20000],
        icon="mdi:transmission-tower",
    ),
]

# ---------------------------------------------------------------------------
# TIME REGISTERS (charging/discharging period start & stop times)
# Each entry writes hour + minute as separate registers but presents as hh:mm.
# The underlying sensor reads (hour_key / minute_key) are in SENSOR_REGISTERS.
# ---------------------------------------------------------------------------
TIME_REGISTERS: list[ModbusTimeDef] = [
    ModbusTimeDef("charging_period_1_start",    "Charging Period 1 Start Time",    0x0856, 0x085E, "mdi:clock-start"),
    ModbusTimeDef("charging_period_1_stop",     "Charging Period 1 Stop Time",     0x0857, 0x085F, "mdi:clock-end"),
    ModbusTimeDef("charging_period_2_start",    "Charging Period 2 Start Time",    0x0858, 0x0860, "mdi:clock-start"),
    ModbusTimeDef("charging_period_2_stop",     "Charging Period 2 Stop Time",     0x0859, 0x0861, "mdi:clock-end"),
    ModbusTimeDef("discharging_period_1_start", "Discharging Period 1 Start Time", 0x0851, 0x085A, "mdi:clock-start"),
    ModbusTimeDef("discharging_period_1_stop",  "Discharging Period 1 Stop Time",  0x0852, 0x085B, "mdi:clock-end"),
    ModbusTimeDef("discharging_period_2_start", "Discharging Period 2 Start Time", 0x0853, 0x085C, "mdi:clock-start"),
    ModbusTimeDef("discharging_period_2_stop",  "Discharging Period 2 Stop Time",  0x0854, 0x085D, "mdi:clock-end"),
]

# ---------------------------------------------------------------------------
# Dispatch register base address (used in switch/button write sequences)
# ---------------------------------------------------------------------------
DISPATCH_START_ADDR = 0x0880

# Dispatch mode values
DISPATCH_MODE_SOC_CONTROL = 2
DISPATCH_SOC_SCALE = 0.392  # %/bit

# Charging/discharging time period control register
CHARGING_TIME_PERIOD_ADDR = 0x084F
