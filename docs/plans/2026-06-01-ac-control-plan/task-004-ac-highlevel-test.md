# Task 004 Test: 高层 API 测试 (Red)

**depends-on**: task-003-ac-app-oper-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 2:

```
Scenario: 开关
Scenario: 设置 HVAC 模式
Scenario: 设置目标温度
Scenario: 设置风速
Scenario: 设置扫风模式
Scenario: 预设模式
```

## 目标

为高层控制 API（`turn_on`/`turn_off`/`set_hvac_mode`/`set_temperature`/`set_fan_mode`/`set_swing_mode`/`set_preset_mode`/`set_electric_heating`）写失败测试。

## 待创建/修改

- 扩展 `tests/test_ac_control.py`
- 暂不实现（Red）

## 测试要点

每个高层函数接收 `(client, device_id, model_id, ...)`，内部调 `app_oper`。Mock client 上的 `app_oper`：

1. `turn_on(client, device_id, model_id)` → `app_oper(client, device_id, model_id, {"C_POWER": "1"})`
2. `turn_off(...)` → `{"C_POWER": "0"}`
3. `set_hvac_mode(..., HvacMode.COOL)` → `{"C_MODE": "1"}`；`HvacMode.HEAT` → `{"C_MODE": "2"}`；`HvacMode.FAN_ONLY` → `{"C_MODE": "3"}`；`HvacMode.DRY` → `{"C_MODE": "4"}`；`HvacMode.AUTO` → `{"C_MODE": "6"}`；`"off"` → `{"C_POWER": "0"}`
4. `set_temperature(..., 24.0)` → `{"C_TEMPERATURE": "24.0"}`；`set_temperature(..., 24)` → `{"C_TEMPERATURE": "24"}`；`set_temperature(..., "abc")` 抛 `ValueError`；`set_temperature(..., 5)` 抛 `ValueError`（低于合理下限）或类似范围校验。
5. `set_fan_mode(..., FanSpeed.AUTO)` → `{"C_FANSPEED": "0"}`；`LOW/MID/HIGH/HIGHER/HIGHEST` → `{"C_FANSPEED": "1/2/3/4/5"}`
6. `set_swing_mode(...)` 4 个枚举对应 SWING_TO_CMD 4 个 dict
7. `set_preset_mode(..., "eco")` → `{"C_ECO": "1"}`；`"none"`（关所有预设） → 发出 `{"C_ECO": "0", "C_FRESHAIR": "0", "C_ELECHEATING": "0"}` 或者文档明确 `"none"` 只关最近一次？**本任务决策：none 表示"关闭所有已支持的预设字段"**，单测验证三种字段都被关。
8. `set_electric_heating(..., on=True)` → `{"C_ELECHEATING": "1"}`；`on=False` → `{"C_ELECHEATING": "0"}`
9. **范围校验**：`set_temperature(..., 10.0)` 抛 `ValueError`（最低 16℃），`set_temperature(..., 40.0)` 抛 `ValueError`（最高 32℃）。具体边界用 16/32 即可。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "highlevel or set_hvac or set_temperature or set_fan or set_swing or set_preset or set_electric or turn_on"
```

**预期**：FAIL。
