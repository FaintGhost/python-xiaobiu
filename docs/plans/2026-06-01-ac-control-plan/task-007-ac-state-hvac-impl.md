# Task 007 Impl: 状态 hvac_mode 推断实现 (Green)

**depends-on**: task-007-ac-state-hvac-test.md

## BDD Scenario

```
Scenario: AirConditionerStatus 增强
```

## 目标

扩展 `client.py` 的 `_normalize_air_conditioner_status`，引入 hvac_mode 推断。

## 待修改

- `src/xiaobiu/client.py`：
  1. 在文件顶部 `from . import ac_control` 引入（**注意**：放在文件底部 import 之后以避免循环；ac_control 引用 `SuningError` 而非 SuningSmartHomeClient，安全）。
  2. 替换 `_build_ha_climate_preview` 内部"模式枚举尚未确认"那段 notes。
  3. 在 `_normalize_air_conditioner_status` 返回前，用 `ac_control.C_FIELD_TO_HVAC` / `ac_control.C_FIELD_TO_FAN` 推断 `hvac_mode` / `fan_mode`：
     ```python
     power_on = _parse_bool_flag(_coalesce(raw_status.get("SN_POWER"), raw_status.get("C_POWER")))
     hvac_mode = ac_control.infer_hvac_mode(
         power_on=power_on,
         mode_raw=_coalesce(raw_status.get("SN_MODE"), raw_status.get("C_MODE")),
     )
     ```
     `infer_hvac_mode` 是 `ac_control.py` 新增的纯函数：
     - `power_on is False` → `"off"`
     - `power_on is True and mode_raw in C_FIELD_TO_HVAC` → 对应枚举
     - 其他 → `None`
  4. 类似 `fan_mode_raw` 可以加 `infer_fan_mode`（可选，本任务也可不实现 fan_mode 推断，只做 hvac_mode；看 004 决定）。
  5. 更新 notes 文案：
     - 删 `"设备当前上报为开机，但模式枚举尚未确认，暂不映射标准 HVACMode。"`
     - 删 `"原始模式值为 ...，后续需要控制抓包后确认枚举含义。"`
     - 新增 `"C_ELECHEATING 字段控制路径未实测，请审慎使用。"`
     - 保留原有的离线/电源未解析等 note。

## 实现细节

- `infer_hvac_mode` 接受字符串 / 整数 / None，统一 `str(value).strip()` 后查表。
- `_build_ha_climate_preview` 改为读 `status.hvac_mode` 而非自己算。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_client.py -x -q
```

**预期**：PASS（且现有 001-006 测试继续 PASS）。
