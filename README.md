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

Suning's "小标" App exposes a flat per-device control surface where every
button on the AC card maps to a single ``C_*`` field on the ``appOper``
endpoint.  This client mirrors that surface and aligns the typed layer
with the [Home Assistant climate entity](https://developers.home-assistant.io/docs/core/entity/climate/).

```python
from xiaobiu import (
  FanSpeed,
  HvacMode,
  PresetMode,
  SwingMode,
)

status = client.get_air_conditioner_status(
  family_id=37790,
  device_id="000165f9b029afa2e5d8",
)
print(status.hvac_mode)  # HvacMode.{OFF,COOL,HEAT,FAN_ONLY,DRY,AUTO,QUICK} or None

# Power
client.turn_on(family_id=37790, device_id="000165f9b029afa2e5d8")
client.turn_off(family_id=37790, device_id="000165f9b029afa2e5d8")

# Mode
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.HEAT)   # 制热 (C_MODE=1)
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.COOL)   # 制冷 (C_MODE=2)
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.DRY)    # 除湿 (C_MODE=3)
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.FAN_ONLY)  # 送风 (C_MODE=4)
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.AUTO)   # 一键通/自动 (C_MODE=6)
client.set_hvac_mode(family_id=37790, device_id="...", mode=HvacMode.QUICK)  # 一键通/自动 (C_MODE=6, 与 AUTO 同)

# Temperature
client.set_temperature(family_id=37790, device_id="...", value=24.0)  # 16.0–32.0

# Fan (App 标签 / C_FANSPEED raw / HA fan_mode)
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.AUTO)    # 自动   / 0 / auto
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.SILENT)  # 微风   / 1 / silent
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.LOW)     # 低风   / 2 / low
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.MEDIUM)  # 中风   / 3 / medium
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.HIGH)    # 高风   / 4 / high
client.set_fan_mode(family_id=37790, device_id="...", speed=FanSpeed.TURBO)   # 强风   / 5 / turbo

# Swing (vertical/horizontal can be toggled independently)
client.set_vertical_swing(family_id=37790, device_id="...", on=True)   # 上下摆风 开
client.set_vertical_swing(family_id=37790, device_id="...", on=False)  # 上下摆风 关
client.set_horizontal_swing(family_id=37790, device_id="...", on=True)  # 左右摆风 开
client.set_horizontal_swing(family_id=37790, device_id="...", on=False)  # 左右摆风 关
# HA convenience setter that writes both fields at once
client.set_swing_mode(family_id=37790, device_id="...", swing=SwingMode.BOTH)

# Presets (each is a single boolean field)
client.set_eco(family_id=37790, device_id="...", on=True)         # ECO 开
client.set_eco(family_id=37790, device_id="...", on=False)        # ECO 关
client.set_fresh_air(family_id=37790, device_id="...", on=True)   # 空气清新 开
client.set_fresh_air(family_id=37790, device_id="...", on=False)  # 空气清新 关
client.set_aux_heat(family_id=37790, device_id="...", on=True)    # 电辅热 开（仅制热）
client.set_aux_heat(family_id=37790, device_id="...", on=False)   # 电辅热 关

# Read side
client.list_device_timers(family_id=37790, device_id="...")
client.get_device_panel_template(family_id=37790, device_id="...")
```

### HA climate entity mapping

| Suning App | `xiaobiu` API | `C_*` field | HA climate field |
|------------|---------------|------------|------------------|
| 电源开关 | `turn_on/off` | `C_POWER` | `hvac_mode = off` when off |
| 制热 | `set_hvac_mode(HEAT)` | `C_MODE=1` | `hvac_mode = heat` |
| 制冷 | `set_hvac_mode(COOL)` | `C_MODE=2` | `hvac_mode = cool` |
| 除湿 | `set_hvac_mode(DRY)` | `C_MODE=3` | `hvac_mode = dry` |
| 送风 | `set_hvac_mode(FAN_ONLY)` | `C_MODE=4` (或 `5`) | `hvac_mode = fan_only` |
| 一键通/自动 | `set_hvac_mode(AUTO)` / `set_hvac_mode(QUICK)` | `C_MODE=6` | `hvac_mode = auto` |
| 微风/低/中/高/强风 | `set_fan_mode(SILENT/LOW/MEDIUM/HIGH/TURBO)` | `C_FANSPEED=1..5` | `fan_mode` |
| 上下摆风 | `set_vertical_swing(on=)` | `C_AIRVERTICAL` | `swing_mode` (HA 把 `swing_mode` 默认指垂直) |
| 左右摆风 | `set_horizontal_swing(on=)` | `C_AIRHORIZONTAL` | `swing_horizontal_mode` |
| ECO | `set_eco(on=)` | `C_ECO` | `preset_mode = eco` |
| 空气清新 | `set_fresh_air(on=)` | `C_FRESHAIR` | `preset_mode = fresh_air` |
| 电辅热 | `set_aux_heat(on=)` | `C_ELECHEATING` | `preset_mode = aux_heat` |

> **读/写编码不同**:上表是**写侧**(`C_MODE` 控制值)。设备**上报状态**用的是另一套 `SN_MODE` 值:
> `SN_MODE=1`(一键通/自动)、`2`(制冷)、`3`(制热)、`4`(送风)、`5`(除湿)。
> `infer_hvac_mode` 读状态时默认按 `SN_MODE` 解码;下发命令时 `set_hvac_mode` 用 `C_MODE`。
> 两套编码不一致(如 `C_MODE=1` 是制热,但 `SN_MODE=1` 是一键通),库内部已拆成两张表分别处理。

### `swing_mode` 集成注意事项

按 Home Assistant climate entity 惯例：

- **`swing_mode` 属性专指垂直摆风**。HA 集成作者应在 `async_set_swing_mode(swing_mode)` 里把 `"vertical"` / `"off"` 映射到 `client.set_swing_mode(SwingMode.VERTICAL)` / `SwingMode.OFF`。
- **`swing_horizontal_mode` 是独立属性**。`"on"` / `"off"` 映射到 `client.set_horizontal_swing(on=True/False)`。
- **`SwingMode.ON` 不支持**。苏宁设备物理上没有"开摆不指定方向"语义——要么 vertical 要么 horizontal，要么都开。HA 集成遇到 `swing_mode = "on"` 时应映射到 `SwingMode.BOTH`（或 `VERTICAL`）。
- **`set_swing_mode(SwingMode.HORIZONTAL)` 与 `set_horizontal_swing(on=True)` 设备层等价**（都把 `C_AIRHORIZONTAL` 设为 1），但**HA 集成应走 `set_horizontal_swing`** 保持与 HA 字段语义一致。`set_swing_mode(SwingMode.HORIZONTAL)` 主要给脚本/手动控制用，一次发两字段。
- **`set_swing_mode(SwingMode.BOTH)` 等价于 `set_vertical_swing(on=True); set_horizontal_swing(on=True)`，但只走一次网络**。HA 集成没有"BOTH"标准值，组合调用更标准。

### `hvac_action` 推断

`AirConditionerStatus.hvac_action` 由 `ac_control.infer_hvac_action` 在 `_normalize_air_conditioner_status` 时填入，推断规则：

| 条件 | 推断 |
|------|------|
| `power_on=False` 或 `hvac_mode=off` | `HvacAction.OFF` |
| `hvac_mode=heat` 且 `current_temp < target_temp` | `HvacAction.HEATING` |
| `hvac_mode=heat` 且 `current_temp >= target_temp` | `HvacAction.IDLE` |
| `hvac_mode=cool` 且 `current_temp > target_temp` | `HvacAction.COOLING` |
| `hvac_mode=cool` 且 `current_temp <= target_temp` | `HvacAction.IDLE` |
| `hvac_mode=dry` | `HvacAction.DRYING` |
| `hvac_mode=fan_only` | `HvacAction.FAN` |
| `hvac_mode=auto` / `heat_cool` | 根据 current vs target 二选一（heating/cooling/idle） |
| `power_on=None`（设备离线） | `HvacAction=None` → HA 渲染 `unavailable` |

### 动态能力表（`DeviceCapabilities`）

`client.get_device_panel_template(family_id, device_id)` 现在返回 `DeviceCapabilities`，从 `queryTemplate.do` 实时解析：

```python
caps = client.get_device_panel_template(family_id=37790, device_id="000165f9b029afa2e5d8")
caps.hvac_modes           # ["off", "cool", "heat", "dry", "fan_only", "auto", "quick"]
caps.fan_modes            # ["auto", "silent", "low", "medium", "high", "turbo"]
caps.swing_modes          # ["off", "vertical", "horizontal", "both"]
caps.preset_modes         # ["none", "eco", "fresh_air", "aux_heat"]
caps.supports_vertical_swing   # True
caps.supports_horizontal_swing # True
caps.supports_eco
caps.supports_fresh_air
caps.supports_aux_heat
caps.fields["C_FANSPEED"].raw_values     # ["0","1","2","3","4","5"]
caps.fields["C_FANSPEED"].display_values  # ["自动","微风","低风","中风","高风","强风"]
caps.fields["C_FANSPEED"].icon_urls       # [6 个图标 URL]
```

HA 集成应在 `async_setup_entry` 时调一次 `get_device_panel_template` 缓存起来，**直接喂给 `hvac_modes` / `fan_modes` / `swing_modes` / `preset_modes` 属性**——不要再硬编码列表。

### `preset_mode` 自定义值

按 HA 文档，自定义 preset 是允许的（"you're also allowed to add custom presets"）。所以 `fresh_air` 和 `aux_heat` 不在 HA 标准列表里，但 HA 集成**可以**把它们放进 `preset_modes` 列表（中文用户友好）或直接用 `aux_heat` 这个 HA 官方名（与 `turn_aux_heat_on/off` 服务对应）。

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
xiaobiucli control              --family-id 37790 --device-id <id> --power on|off
xiaobiucli set-mode             --family-id 37790 --device-id <id> --mode off|cool|heat|fan_only|dry|auto|quick
xiaobiucli set-temperature      --family-id 37790 --device-id <id> --temperature 24.0
xiaobiucli set-fan              --family-id 37790 --device-id <id> --speed auto|silent|low|medium|high|turbo
xiaobiucli set-swing            --family-id 37790 --device-id <id> --mode off|vertical|horizontal|both
xiaobiucli set-vertical-swing   --family-id 37790 --device-id <id> --on|--off
xiaobiucli set-horizontal-swing --family-id 37790 --device-id <id> --on|--off
xiaobiucli set-eco              --family-id 37790 --device-id <id> --on|--off
xiaobiucli set-fresh-air        --family-id 37790 --device-id <id> --on|--off
xiaobiucli set-aux-heat         --family-id 37790 --device-id <id> --on|--off
xiaobiucli timers               --family-id 37790 --device-id <id>
xiaobiucli panel                --family-id 37790 --device-id <id>
xiaobiucli raw-oper             --family-id 37790 --device-id <id> --cmd C_MODE=1 [--cmd KEY=VALUE ...]
```

## Notes

- **`C_MODE` / `SN_MODE` 编码不同**(2026-06-17 真机实测确认):
  - 写侧 `C_MODE`:`1`=制热、`2`=制冷、`3`=除湿、`4`=送风、`5`=送风(同 4)、`6`=一键通(≈自动)
  - 读侧 `SN_MODE`:`1`=一键通(自动)、`2`=制冷、`3`=制热、`4`=送风、`5`=除湿
  - 库内部用 `C_FIELD_TO_HVAC`(写)和 `SN_FIELD_TO_HVAC`(读)两张表分别处理。
- **一键通 ≈ 自动**:这台设备没有独立的 AUTO 模式,`C_MODE=6`(一键通)在语义上最接近,
  暴露为 `HvacMode.AUTO`;`HvacMode.QUICK` 也指向 `C_MODE=6`。
- **`C_ELECHEATING` (电辅热)** 值域已实测确认为 `0/1`。`set_aux_heat(on=True)` 在客户端
  强制 App 的"仅制热时生效"规则(当前模式非 HEAT 时 raise `SuningError`)。
- **`SN_CLOUD_TIMER` writes** are not implemented in this release.
- **Unknown `C_MODE` values** (e.g. `7`, which neither the App nor the
  capture expose) collapse to `hvac_mode = None` so Home Assistant can
  render `unavailable` rather than guessing.

## Requirements

- Python >= 3.14
- `cryptography`, `pydantic`, `requests`
