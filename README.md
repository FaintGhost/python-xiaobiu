# python-xiaobiu

Python client for Suning smart home SMS login and session management.

Used by the [ha-suning](https://github.com/FaintGhost/ha-suning) Home Assistant custom integration.

## Install

```bash
pip install python-xiaobiu
```

## Usage

```python
from xiaobiu import CaptchaRequiredError, SuningSmartHomeClient

client = SuningSmartHomeClient(state_path=".suning-session.json")

try:
    client.send_sms_code("13800000000")
except CaptchaRequiredError as error:
    print(error.risk_type, error.sms_ticket)

client.login_with_sms_code(phone_number="13800000000", sms_code="123456")
print(client.list_family_infos())
```

## Air Conditioner Control

```python
from xiaobiu import (
  FanSpeed,
  HvacMode,
  PanelTemplate,
  PresetMode,
  SwingMode,
  Timer,
)

# Status — the HA preview is now driven by the typed hvac_mode.
status = client.get_air_conditioner_status(family_id=37790, device_id="000165f9b029afa2e5d8")
print(status.hvac_mode)         # HvacMode.COOL / HEAT / FAN_ONLY / DRY / AUTO / OFF / None
print(status.ha_climate_preview.notes)

# Power
client.turn_on(family_id=37790, device_id="000165f9b029afa2e5d8")
client.turn_off(family_id=37790, device_id="000165f9b029afa2e5d8")

# Mode / temperature / fan / swing
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.COOL)
client.set_temperature(family_id=37790, device_id="...", value=24.0)   # 16.0–32.0
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.LOW)
client.set_swing_mode(family_id=37790, device_id="...", swing=SwingMode.VERTICAL)

# Presets
client.set_preset_mode(family_id=37790, device_id="...", preset=PresetMode.ECO)
client.set_preset_mode(family_id=37790, device_id="...", preset=PresetMode.NONE)  # turn ECO+FRESH_AIR+ELECHEATING off
client.set_electric_heating(family_id=37790, device_id="...", on=False)          # see Notes

# Timers / panel template
timers: list[Timer] = client.list_device_timers(family_id=37790, device_id="...")
template: PanelTemplate | None = client.get_device_panel_template(
  family_id=37790,
  device_id="000165f9b029afa2e5d8",
)
```

## CLI

```bash
# Interactive login
xiaobiucli login --phone 13800000000 --state-file .suning-session.json

# Send SMS only
xiaobiucli send-sms --phone 13800000000 --state-file .suning-session.json

# Check session
xiaobiucli check --state-file .suning-session.json

# List families / devices
xiaobiucli families --state-file .suning-session.json
xiaobiucli devices --family-id 37790 --state-file .suning-session.json

# Air-conditioner control
xiaobiucli control         --family-id 37790 --device-id <id> --power on|off
xiaobiucli set-mode        --family-id 37790 --device-id <id> --mode off|cool|heat|fan_only|dry|auto
xiaobiucli set-temperature --family-id 37790 --device-id <id> --temperature 24.0
xiaobiucli set-fan         --family-id 37790 --device-id <id> --speed auto|low|mid|high|higher|highest
xiaobiucli set-swing       --family-id 37790 --device-id <id> --mode off|vertical|horizontal|both
xiaobiucli set-preset      --family-id 37790 --device-id <id> --preset none|eco|fresh_air
xiaobiucli timers          --family-id 37790 --device-id <id>
xiaobiucli panel           --family-id 37790 --device-id <id>
```

## Notes

- `C_ELECHEATING` (电加热) was discovered via `queryTemplate.do` but **the control path was not exercised in the 2026-06-01 capture**; the value is inferred to be `0/1`. Treat `set_electric_heating` with care until it is verified against a live device.
- `SN_CLOUD_TIMER` writes are **not implemented** in this release. Only the timer list (read via `xiaobiucli timers`) is exposed.
- The typed `hvac_mode` inference collapses unknown `C_MODE` values (e.g. `5`, which the capture did not surface) to `None` so Home Assistant can render `unavailable` rather than guessing.

## Requirements

- Python >= 3.14
- `cryptography`, `pydantic`, `requests`
