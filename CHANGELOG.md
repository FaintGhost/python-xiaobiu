# Changelog

All notable changes to `python-xiaobiu` are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-06-02

### Added
- `HvacAction` enum (`OFF` / `PREHEATING` / `HEATING` / `COOLING` /
  `DRYING` / `FAN` / `IDLE` / `DEFROSTING`) and
  `AirConditionerStatus.hvac_action` field, inferred from
  `power_on × hvac_mode × current_temp vs target_temp` so HA can
  render the live state of the AC.
- `DeviceCapabilities` / `CapabilityField` models driven by the
  device's panel template.  `client.get_device_panel_template()`
  now returns a `DeviceCapabilities` with `hvac_modes` /
  `fan_modes` / `swing_modes` / `preset_modes` lists and per-field
  metadata (raw / display / icon URLs) parsed from `queryTemplate.do`.
  This lets HA integrators advertise exactly what the device supports
  instead of hard-coding the lists.

### Changed
- README "Air Conditioner Control" section now documents
  `hvac_action` inference rules and shows a `DeviceCapabilities`
  usage snippet.

## [0.2.0] - 2026-06-02

### Added
- Air-conditioner control surface: `turn_on` / `turn_off` / `set_hvac_mode` /
  `set_temperature` / `set_fan_mode` / `set_swing_mode` / `set_preset_mode` /
  `app_oper` on `SuningSmartHomeClient`.
- Independent boolean setters (HA-aligned): `set_eco` / `set_fresh_air` /
  `set_aux_heat` / `set_vertical_swing` / `set_horizontal_swing`.
- `HvacMode.QUICK` for the inferred one-touch mode (C_MODE=5).
- Device introspection: `get_device_panel_template` / `list_device_timers`.
- Typed enums aligned with the
  [Home Assistant climate entity](https://developers.home-assistant.io/docs/core/entity/climate/):
  `HvacMode` / `FanSpeed` / `SwingMode` / `PresetMode` / `PanelTemplate` / `Timer`.
- Strongly-typed `hvac_mode` inference in `AirConditionerStatus` from the
  raw `C_MODE` / `SN_MODE` + `C_POWER` fields (offline devices report
  `None`).
- New CLI sub-commands: `control`, `set-mode`, `set-temperature`,
  `set-fan`, `set-swing`, `set-vertical-swing`, `set-horizontal-swing`,
  `set-eco`, `set-fresh-air`, `set-aux-heat`, `timers`, `panel`.
- `set_aux_heat(on=True)` enforces the App's "aux heat only while
  heating" rule (raises `SuningError` if the current `hvac_mode` is
  not `HEAT`).
- `AirConditionerStatus.ha_climate_preview.notes` now surfaces the raw
  `C_ELECHEATING` field when the device reports it.

### Changed
- **Breaking**: `FanSpeed` enum values renamed to match HA climate
  fan modes — `LOW→SILENT`, `MID→LOW`, `HIGH→MEDIUM`, `HIGHER→HIGH`,
  `HIGHEST→TURBO`. The `C_FANSPEED` raw value mapping (0..5) is
  unchanged.
- **Breaking**: `set_hvac_mode(HvacMode.OFF)` no longer sends
  `{"C_MODE": "0"}`; it powers the device off via `{"C_POWER": "0"}`.
- `AirConditionerStatus` now carries a typed `hvac_mode` field (was
  implicit / `None`).
- `client._resolve_ac_target` reads the `model` field returned by
  the live `list_devices` endpoint (was `modelId`).
- README: "Air Conditioner Control" section now includes a HA
  climate entity mapping table and a Notes section flagging
  `C_ELECHEATING` (untested) and `SN_CLOUD_TIMER` (writes not
  implemented).

### Removed
- **Breaking**: `SuningSmartHomeClient.set_electric_heating()` and
  `ac_control.set_electric_heating()` were removed. Use
  `set_aux_heat(on=...)` instead.

### Refactored
- `client.py` (1990 lines, 36 defs/classes, god class) was split
  into 8 focused modules: `exceptions`, `parsers`, `persistence`,
  `app_api`, `sms_login`, `har_templates`, `ac_status`, `cli`.
  `client.py` is now a 687-line thin façade with re-exports for
  full backward compatibility of the public API.
- `tests/test_client.py` (1033 lines) was split into 7 focused test
  files matching the new module boundaries.

## [0.1.1] - 2026-03-22

### Fixed
- `list_devices` now decodes the device payload shape returned by the
  live API (familyId / id field).

## [0.1.0] - 2026-03-21

### Added
- Initial release: SMS login, captcha bridge, session persistence,
  family / device enumeration, basic air-conditioner status read.
- `xiaobiucli` with `login`, `send-sms`, `check`, `families`,
  `devices`, `device-status`, `keep-alive` sub-commands.
