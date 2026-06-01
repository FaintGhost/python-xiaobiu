# 空调控制对齐 HA climate — BDD Specs

> 来源：2026-06-02 真实设备验证 + HA 官方 climate entity 文档
> 设计目标：把枚举名 / setter 粒度 / CLI 全部对齐 HA climate 标准 + 用户 App 实际能力。

## HA climate 文档关键事实

- **HVACMode**: `off` / `heat` / `cool` / `heat_cool` / `auto` / `dry` / `fan_only`
- **Fan modes**: `on` / `off` / `auto` / `low` / `medium` / `high` / `middle` / `focus` / `diffuse`
- **Swing modes**: `off` / `on` / `vertical` / `horizontal` / `both`
- **Swing horizontal modes** 独立：`off` / `on`（HA 提供 `SWING_HORIZONTAL_MODE` feature flag）
- **Preset modes**: `none` / `eco` / `away` / `boost` / `comfort` / `home` / `sleep` / `activity`
- `aux_heat` 不是 preset_mode —— HA 通过 `ClimateEntityFeature.AUX_HEAT` + `turn_aux_heat_on/off` 服务控制

## 实际设备（HAR + 真实）能力清单

| App 标签 | C 字段 | 推断 raw | 设计枚举 |
|----------|--------|---------|----------|
| 自动 | C_FANSPEED | 0 | `FanSpeed.AUTO` (`auto`) |
| 微风 | C_FANSPEED | 1 | `FanSpeed.SILENT` (`silent`) |
| 低风 | C_FANSPEED | 2 | `FanSpeed.LOW` (`low`) |
| 中风 | C_FANSPEED | 3 | `FanSpeed.MEDIUM` (`medium`) |
| 高风 | C_FANSPEED | 4 | `FanSpeed.HIGH` (`high`) |
| 强风 | C_FANSPEED | 5 | `FanSpeed.TURBO` (`turbo`) |
| 自动 | C_MODE | 6 | `HvacMode.AUTO` (`auto`) |
| 制冷 | C_MODE | 1 | `HvacMode.COOL` (`cool`) |
| 制热 | C_MODE | 2 | `HvacMode.HEAT` (`heat`) |
| 送风 | C_MODE | 3 | `HvacMode.FAN_ONLY` (`fan_only`) |
| 除湿 | C_MODE | 4 | `HvacMode.DRY` (`dry`) |
| **一键通** | C_MODE | **5 (推断)** | `HvacMode.QUICK` (`quick`) — 待用户在 App 上验证 |
| 上下摆风 | C_AIRVERTICAL | 0/1 | `set_vertical_swing(on)` 独立 |
| 左右摆风 | C_AIRHORIZONTAL | 0/1 | `set_horizontal_swing(on)` 独立 |
| ECO | C_ECO | 0/1 | `set_eco(on)` 独立 |
| 空气清新 | C_FRESHAIR | 0/1 | `set_fresh_air(on)` 独立 |
| 电辅热 | C_ELECHEATING | 0/1 | `set_aux_heat(on)` 独立（**仅在 mode=heat 时生效**） |

## 设计决策

1. **FanSpeed 彻底重命名**：删 LOW/MID/HIGH/HIGHER/HIGHEST，改 AUTO/SILENT/LOW/MEDIUM/HIGH/TURBO。
   C_FANSPEED raw 值映射保持：0=AUTO, 1=SILENT, 2=LOW, 3=MEDIUM, 4=HIGH, 5=TURBO。
2. **HvacMode 加 QUICK**：raw=5。`infer_hvac_mode` 也认 5。
3. **拆粒度**：
   - 摆风：删 NONE 联动的 set_preset_mode(NONE)，加独立 `set_vertical_swing` / `set_horizontal_swing`
   - 预设：删 `set_preset_mode(PresetMode.NONE)` 全关，加独立 `set_eco` / `set_fresh_air` / `set_aux_heat`
4. **保留组合 setter**：`set_swing_mode(SwingMode.OFF/VERTICAL/HORIZONTAL/BOTH)` 用于 HA 集成映射。
5. **电辅热前置**：调 `set_aux_heat(on=True)` 前 `get_air_conditioner_status`，若 hvac_mode 不在 {HEAT, None} 则 raise `SuningError("电辅热仅在制热模式下生效")`。读状态失败时**不**阻断（HAR 没确认规则，宁可让用户自己保证）。
6. **CLI 子命令**：
   - `set-fan` `--speed` choices 改成 `auto/silent/low/medium/high/turbo`
   - `set-mode` `--mode` choices 增 `quick`
   - 新增 `set-eco` `--on/--off`
   - 新增 `set-fresh-air` `--on/--off`
   - 新增 `set-aux-heat` `--on/--off`
   - 新增 `set-vertical-swing` `--on/--off`
   - 新增 `set-horizontal-swing` `--on/--off`
   - **删除** `set-preset`（被上面 5 个细分命令取代；用户 App 上没有"preset"概念）
   - 保留 `set-swing`（组合用）

## BDD Scenarios

### Scenario 1: FanSpeed 重命名
```
Given 重命名后的 FanSpeed 枚举
When 写 C_FIELD_TO_FAN
Then 0 -> AUTO / 1 -> SILENT / 2 -> LOW / 3 -> MEDIUM / 4 -> HIGH / 5 -> TURBO
And 旧 LOW(1) -> SILENT / MID(2) -> LOW / HIGH(3) -> MEDIUM / HIGHER(4) -> HIGH / HIGHEST(5) -> TURBO
```

### Scenario 2: HvacMode.QUICK
```
Given HvacMode 枚举
When 写 C_FIELD_TO_HVAC
Then 5 -> HvacMode.QUICK（"一键通"）
And infer_hvac_mode(power_on=True, mode_raw="5") == HvacMode.QUICK
And set_hvac_mode(QUICK) 发出 {"C_MODE": "5"}
```

### Scenario 3: 摆风独立
```
Given 已知 device
When set_vertical_swing(client, family_id, device_id, on=True)
Then 内部发送 {"C_AIRVERTICAL": "1"}
When on=False
Then {"C_AIRVERTICAL": "0"}
And set_horizontal_swing 同理（独立于 vertical）
```

### Scenario 4: 预设独立
```
When set_eco(client, family_id, device_id, on=True)
Then {"C_ECO": "1"}
When on=False
Then {"C_ECO": "0"}
And set_fresh_air 走 C_FRESHAIR
And set_aux_heat 走 C_ELECHEATING
```

### Scenario 5: 电辅热前置
```
Given 设备当前 hvac_mode=cool
When set_aux_heat(client, family_id, device_id, on=True)
Then 抛 SuningError("电辅热仅在制热模式下生效")
And 内部不调用 app_oper
Given 设备 hvac_mode=heat
When set_aux_heat(on=True)
Then {"C_ELECHEATING": "1"}
```

### Scenario 6: CLI 新子命令
```
When xiaobiucli set-fan --speed turbo
Then set_fan_mode(FanSpeed.TURBO)
And xiaobiucli set-mode --mode quick 解析为 HvacMode.QUICK
And xiaobiucli set-eco --on / --off 解析为 boolean
And xiaobiucli set-vertical-swing --on/--off 解析为 boolean
And xiaobiucli set-preset 已被移除
```

## 架构调整

- `src/xiaobiu/ac_control.py`：
  - FanSpeed 枚举值全改；C_FIELD_TO_FAN 同步改
  - C_FIELD_TO_HVAC 加 "5": QUICK
  - 删 `set_preset_mode(PresetMode.NONE)` 全关的逻辑；改 `set_preset_mode(preset: PresetMode)` 调 on-cmd
  - 加 `set_vertical_swing(client, device_id, model_id, *, on: bool)`
  - 加 `set_horizontal_swing(client, device_id, model_id, *, on: bool)`
  - 加 `set_eco(client, device_id, model_id, *, on: bool)`
  - 加 `set_fresh_air(client, device_id, model_id, *, on: bool)`
  - 加 `set_aux_heat(client, device_id, model_id, *, on: bool)`（读 status 前置）
- `src/xiaobiu/client.py`：
  - `SuningSmartHomeClient` 同步加 6 个新方法（family_id/device_id 解析后转调 ac_control）
  - `_build_parser`：删 set-preset，加 set-eco/set-fresh-air/set-aux-heat/set-vertical-swing/set-horizontal-swing；set-fan choices 改；set-mode choices 加 quick
  - `main` 分支更新
- `src/xiaobiu/models.py`：FanSpeed 值改；HvacMode 加 QUICK
- `src/xiaobiu/__init__.py`：导出更新
- `README.md`：重写 "Air Conditioner Control" + CLI 章节，反映新枚举名 + 新子命令
- `tests/test_ac_control.py`：删旧 LOW/MID/HIGH/HIGHER/HIGHEST 测试，加新 SILENT/LOW/MEDIUM/HIGH/TURBO + 独立 setter + 电辅热前置
- `tests/test_client.py`：删 set-preset 解析测试，加新 5 个子命令 + 新 choices

## 风险

- `C_MODE=5` 是推断的"一键通"，用户需在真实设备上点一次确认 C_MODE=5 真对应一键通（不是别的）。如果错了，需要在 spec 里改。
- `infer_hvac_mode` 加了 5 → QUICK 后，可能影响既有 `assert hvac_mode == "cool"` 之类测试（如果设备 status 里出现 C_MODE=5 但用户认为是其他）。需要确认。
- 真实设备 set_aux_heat 在非制热模式下，服务端可能直接拒绝，也可能接受但无效。HAR 没测过。先 client 端阻止（raise），等真机反馈再决定要不要放开。

## 不做

- SN_CLOUD_TIMER 写入（按用户要求）
- 不重写 HAClimatePreview 字段（已对齐）
- 不动主客户端登录 / session 流程
