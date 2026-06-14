# Changelog

### v1.15.0-beta.1

#### What's new

- Connection settings (IP address, port, Slave ID) can now be changed without removing and re-adding the integration. A "Reconfigure" option appears in the three-dot menu on the AlphaESS card in Settings > Devices & Services. The new settings are connection-tested before saving, and the integration reloads automatically on success.

#### Upgrading from v1.14.0

- No entities are renamed, removed, or added. No existing settings are affected. The only change is the addition of the Reconfigure option.

---

### v1.14.0

#### What's new

- Changing the power or cutoff SoC of a running force operation (Force Charging, Force Discharging, Force Export, Force Import) or the generic Dispatch now takes effect immediately without restarting the duration countdown. The original stop time is preserved; only changing the duration restarts the countdown. Previously any change to a running operation restarted the countdown, so it could run longer than intended unless you turned it off manually.

#### Bug fixes

- Force Export and Force Import now hold the grid at the target power steadily instead of oscillating. The power was being recalculated from a house-load figure that already included the battery's own output, which fed back on itself and could make the battery swing between roughly 1 kW and 4 kW every couple of seconds at a low export target. The control now adjusts the battery directly against the measured grid power, so export and import sit at the set target and recover smoothly after a sudden load change, with no grid import at low settings.

#### Upgrading from v1.13.1

- No entities are renamed, removed, or added, so dashboards and automations are unaffected. There are no new settings. Two behaviour changes: adjusting power or cutoff SoC while a force operation is running no longer extends the countdown (only changing the duration does), and Force Export and Force Import regulate more smoothly and accurately. If you have an automation that relied on the countdown restarting when the power changed, update the duration instead.

---

### v1.13.1

#### Bug fixes

- Home Assistant now recovers its Modbus connection to the inverter after a router restart. Previously a router reset could leave the connection stuck in a state that never recovered on its own, so sensors went unavailable and controls stopped working until Home Assistant or the integration was restarted. The integration now detects a dead or half-open connection, closes it, and reconnects cleanly on the next poll. This also makes recovery reliable when a force operation or automation is running at the time of the interruption.
- Force Export and Force Import now adjust the battery dispatch as soon as house load or solar changes, instead of waiting for a fixed 25-second cycle. At low export power settings a sudden load such as a kettle could previously pull power from the grid for up to 25 seconds before the next adjustment; it is now corrected within about a poll cycle (a couple of seconds), which matters for zero-import export tariffs.

#### Upgrading from v1.13.0

- No entities are renamed, removed, or added, so dashboards and automations are unaffected. There are no new settings. This release only improves connection recovery after a network interruption and how quickly Force Export and Force Import react to load and solar changes.

---

### v1.13.0

#### What's new

- Dispatch PV Enabled switch added. Controls the inverter's PV coupling during an active dispatch via register 0x088A, so PV can be enabled or disabled mid-dispatch (useful for shedding solar during negative-price periods). Defaults to on (PV enabled). Toggling it while a dispatch is running applies immediately; otherwise it takes effect on the next dispatch.
- All dispatch writes now include the flow-direction and PV-switch registers, extending the dispatch block from 9 to 11 registers (0x0880 to 0x088A). Confirmed on hardware: the PV switch only takes effect during an active dispatch, and the inverter restores PV to normal when the dispatch ends.

#### Bug fixes

- The Dispatch PV Enabled switch and the dispatch countdown now resolve correctly in the example dashboards; their entity IDs were wrong, which showed "Entity not found" on the Dispatch card.
- The write_register service no longer returns an error caused by internal data that is not a coordinator.
- The IP Method diagnostic sensor no longer errors when enabled. It reports a text value (DHCP or Static) but was classed as a numeric measurement, which Home Assistant rejects. It is disabled by default, so this only affected users who had enabled it.
- The Force Discharging Hold switch now has its own translation entry, matching the other Hold switches.
- Several integer diagnostic sensors (system time fields, Modbus baud rate, grid regulation) now display as whole numbers instead of decimals. All are disabled by default.

#### Upgrading from v1.12.0

- No entities are renamed or removed, so existing dashboards and automations are unaffected. The only new entity is the Dispatch PV Enabled switch, which defaults to on (PV stays enabled). Because the generic Dispatch now also sets the PV register, please report any unexpected PV behaviour during a dispatch.

---

### v1.12.0

#### What's new

- Six daily energy sensors added: Today's PV Generation, Today's Energy Feed to Grid, Today's Energy from Grid, Today's Battery Charged, Today's Battery Discharged, and Today's Battery Charged from Grid. Each resets at midnight using the inverter's lifetime cumulative totals as a baseline. State is preserved across HA restarts.

#### Bug fixes

- Today's PV Generation now includes energy from AC-coupled inverters. The hardware register only counts DC string PV; AC-coupled generation is now accumulated via a Riemann sum on the live AC PV meter reading and added to the daily total. The `ac_accumulated_kwh` attribute on the sensor shows the AC portion separately for verification.
- Daily energy sensor entity IDs corrected. The apostrophe in "Today's" caused HA to slugify names to `today_s_*` instead of `today_*`. Sensors now use translation keys so IDs are `today_energy_feed_to_grid`, `today_pv_generation`, etc. **Users upgrading from beta.1 should delete the old `today_s_*` entities from the entity registry after reloading the integration.**
- Force Charging, Discharging, Export, and Import countdown sensors now count down in real time. Previously they read a static hardware register that holds the initial duration and never decrements.
- Force Export and Force Import periodic power recalculation (every 25 s) no longer resets the countdown timer. The countdown now runs from the start of the session instead of restarting every 25 s.
- All countdown sensors now display in minutes by default instead of raw seconds. Existing entities may need the display unit changed in entity settings.

---

### v1.11.0

#### What's new

- Force Export Hold switch added. Enabling it before starting Force Export keeps the dynamic export running indefinitely after the duration expires.
- Force Discharging Hold switch added. Enabling it before starting Force Discharging keeps the session running for the full configured duration instead of stopping early when the SoC target is reached.
- Smart Export removed. It provided the same continuous dynamic export that Force Export Hold now covers. Users who relied on Smart Export should switch to Force Export with Force Export Hold enabled.
- Poll speed presets (Slow, Normal, Fast) added to integration options. Slow reduces the Modbus transaction rate for RS485-to-TCP adapter users prone to timeouts. Fast halves poll intervals and tightens the coordinator loop for faster SoC tracking and tighter dispatch control.
- Raw register write service (`alphaess_modbus.write_register`) added for advanced users. Writes any single register by address and integer value via Developer Tools or automations, with no scale or offset applied.
- B3 and B3PLUS model variant option added to integration options. Selecting B3/B3PLUS applies the correct scale factors for registers that differ from standard AlphaESS inverters.
- Per-mode dispatch countdown sensors added: Force Charging Countdown, Force Discharging Countdown, Force Export Countdown, and Force Import Countdown. Each shows remaining dispatch time only while its switch is active.

#### Bug fixes

- Force Export now dynamically calculates battery discharge power from live house load and PV production so the grid sees the configured feed-in rate. Previously it sent the target directly as battery discharge power, ignoring house load and PV entirely.
- Fast mode poll floor removed. The coordinator loop interval now tracks the Fast Mode Poll Interval directly, allowing sub-1 s polling for direct Modbus TCP connections. Previously the loop was hardcoded to 1 s in Fast mode.
- Excess Export power calculation corrected to charge the battery when PV production exceeds the Inverter AC Limit, instead of always writing zero power.
- Excess Export auto-pause now fires immediately on a work-mode fault instead of waiting up to 15 seconds.
- Excess Export now recalculates battery charge power on every coordinator update (every 2 s) and rewrites dispatch registers when power changes by 50 W or more, keeping pace with changing PV conditions.
- Excess Export dispatch registers could be re-written after the switch was turned off if a resume was in progress; an on-guard check now prevents this.
- All four Force modes (Charging, Discharging, Export, Import) now stop automatically when battery power stays within +/-50 W for 10 consecutive seconds, using the inverter's natural signal that it has reached its SoC target. Force Charging and Force Import previously had no early-stop watcher at all.
- Hold switches (Force Charging Hold, Force Export Hold, Force Import Hold, Force Discharging Hold) no longer keep the inverter in an indefinite hold loop after the duration expires. They now only gate the battery power watcher; the duration timer always stops the mode.
- Force Discharging and Force Export no longer schedule an orphan duration timer when SoC is already at or below the cutoff at startup. The orphan timer would call async_reset_dispatch hours later and could cancel an unrelated active dispatch.

### v1.10.0
- **feat:** Dispatch PV Switch sensor is now enabled by default.
- **feat:** Local IP, Subnet Mask, and Gateway sensors now display as dotted-decimal strings (e.g. `10.0.0.209`) instead of raw integers. IP Method shows `DHCP` or `Static`.
- **feat:** New Dispatch Time Remaining sensor (`sensor.alphaess_inverter_dispatch_countdown`) counts down from the configured dispatch duration in real time.
- **feat:** Battery Status sensor now shows a human-readable label alongside the raw value, e.g. "Charging + Discharging (257)" instead of just "257".
- **feat:** Dispatch Time sensor now shows a human-readable duration string (e.g. "3h 00m", "30m") instead of raw seconds with a thousands separator.
- **fix:** Local IP, Subnet Mask, and Gateway sensors were missing `state_class=None`, causing a `ValueError` on HA startup that prevented those entities from loading.
- **fix:** Battery Capacity scale corrected from 0.001 to 0.1 (reported values were 100x too small). Also fixes Battery Remaining Time which depends on the capacity value.
- **fix:** Battery Remaining Time always returned 0 on ALD-series inverters. Now calculated from live SoC, capacity, and battery power.
- **fix:** Excess Export Pause binary sensor was displaying "Pause" instead of "Excess Export Pause".
- **fix:** Force Import Pause binary sensor was displaying the full device-prefixed name instead of "Force Import Pause".

### v1.9.5
- **fix:** Battery Status sensor now displays as an integer instead of a float (e.g. `1` not `1.0`).
- **fix:** Force Import Hold switch now displays the correct icon (`mdi:battery-lock`); the previously assigned `mdi:transmission-tower-lock` does not exist in the MDI icon set bundled with Home Assistant.
- **fix:** BMS Version, LMU Version, and ISO Version sensors now have `state_class: None`, preventing a `ValueError` that crashed the coordinator update loop after every initial load in recent HA versions.
- **fix:** Register-backed number sliders (Charging/Discharging Cutoff SoC, Max Feed to Grid) now update immediately when written instead of reverting until the next poll cycle.
- **fix:** Force Discharging, Force Export, and Force Import duration sliders now correctly write the configured duration to the inverter (previously hardcoded to 60, 60, and 30 seconds respectively).
- **fix:** Dispatch Power slider now initialises to 0 kW on first install instead of the slider minimum (-20 kW).
- **fix:** Force Import Pause converted from a writable switch to a read-only binary sensor, consistent with Excess Export Pause.
- **fix:** Added `icons.json` so all entities correctly display their icons in Home Assistant 2024.6+.
- **fix:** Dispatch SoC and related dispatch-block sensors no longer show float artefacts (e.g. 99.96% instead of 100%).
- **fix:** SoC threshold sliders across all dispatch modes renamed from "Cutoff SoC" to "Stop at SoC" for consistency. Entity IDs are unchanged.
- **fix:** BMS Version, LMU Version, and ISO Version sensors now display in V1.65 format instead of the raw integer (165).
- **fix:** Four raw EMS version registers are now combined into a single EMS Version sensor (e.g. V1.0.23R1). The raw sub-registers are still polled but disabled by default.
- **fix:** Inverter model detection now uses a known-prefix lookup table (e.g. ALD -> Alphastore, SMILE-B3, SMILE-T10) before falling back to year-based regex parsing, giving more descriptive model names in the HA device card.

### v1.9.4
- **feat:** Excess Export now automatically pauses when the house load would cause grid import and resumes once PV production recovers. Excess Export Pause changed from a writable switch to a read-only binary sensor.

### v1.9.3
- **fix:** inverter model and serial number are now read from the device on startup and shown in the HA device card, replacing the hardcoded "SMILE-M5-S-INV / SMILE series" string.
- **fix:** integer sensor registers (dispatch mode, EMS version, fault/warning codes, period hours/minutes, etc.) no longer display with a spurious `.0` decimal suffix.
- **fix:** power sliders (force charge/discharge/export/import, dispatch power, max export power) now clamp to the configured Inverter AC Limit instead of always allowing up to 20 kW.

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
- **feat:** batch contiguous Modbus register reads - adjacent registers (gap <= 4) are merged into a single `read_holding_registers` call per cycle, reducing typical transaction count from ~50 to ~10 per poll. Coordinator poll interval bumped from 1 s to 2 s; per-sensor `scan_interval` cadence is unchanged.
- **feat:** SOC watcher samples battery SoC every 2 s (down from 10 s) while a force-discharge, force-export, or SOC-watcher switch is active, tightening the cutoff margin for the zero-grid-draw invariant.
- **feat:** number and select sliders now source their displayed value from live coordinator data (the actual inverter register) rather than the last HA-saved state after a restart - so the UI immediately reflects changes made via the AlphaESS app or another client.
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
