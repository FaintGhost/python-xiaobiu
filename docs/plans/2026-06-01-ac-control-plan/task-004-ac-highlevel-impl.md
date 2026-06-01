# Task 004 Impl: 高层 API 实现 (Green)

**depends-on**: task-004-ac-highlevel-test.md

## BDD Scenario

```
Scenario: 开关 / HVAC 模式 / 目标温度 / 风速 / 扫风 / 预设
```

## 目标

在 `ac_control.py` 实现所有高层 API。

## 待创建/修改

- **新建** `src/xiaobiu/ac_control.py`（已在 003 中创建，本任务追加）：

  ```python
  TEMP_MIN_C = 16.0
  TEMP_MAX_C = 32.0
  TEMP_STEP_C = 0.5  # 文档/HAR 显示 0.1 步进可支持，但 0.5 步进是常见下限

  def _validate_temperature(value: float) -> float:
      if not (TEMP_MIN_C <= value <= TEMP_MAX_C):
          raise ValueError(f"target temperature {value} out of range [{TEMP_MIN_C}, {TEMP_MAX_C}]")
      return round(value, 1)

  def turn_on(client, device_id, model_id) -> dict:
      return app_oper(client, device_id, model_id, {"C_POWER": "1"})

  def turn_off(client, device_id, model_id) -> dict:
      return app_oper(client, device_id, model_id, {"C_POWER": "0"})

  def set_hvac_mode(client, device_id, model_id, mode) -> dict:
      """mode: HvacMode 或 'off'。'off' 走 turn_off；其余走 C_MODE 映射。"""
      ...

  def set_temperature(client, device_id, model_id, value) -> dict:
      v = _validate_temperature(float(value))
      return app_oper(client, device_id, model_id, {"C_TEMPERATURE": str(v)})

  def set_fan_mode(client, device_id, model_id, speed) -> dict: ...

  def set_swing_mode(client, device_id, model_id, swing) -> dict: ...

  def set_preset_mode(client, device_id, model_id, preset) -> dict:
      """preset: PresetMode
      - 'eco' 开 C_ECO=1
      - 'fresh_air' 开 C_FRESHAIR=1
      - 'none' 关所有三个预设字段（ECO/FRESHAIR/ELECHEATING）=0
      """
      ...

  def set_electric_heating(client, device_id, model_id, *, on: bool) -> dict: ...
  ```

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q
```

**预期**：与 001-003 一起，全部 PASS。
