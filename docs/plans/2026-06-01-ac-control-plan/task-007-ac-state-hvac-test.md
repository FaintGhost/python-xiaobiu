# Task 007 Test: 状态 hvac_mode 推断测试 (Red)

**depends-on**: task-001-ac-enums-impl.md, task-002-ac-cmd-mappings-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 3:

```
Scenario: AirConditionerStatus 增强
Given 拉取到的设备 dict
When 调 _normalize_air_conditioner_status
Then hvac_mode 不再总是 None —— 能根据 C_POWER + C_MODE 推断出
  - C_POWER=0 -> "off"
  - C_POWER=1 + C_MODE=1 -> "cool"
  - C_POWER=1 + C_MODE=2 -> "heat"
  - C_POWER=1 + C_MODE=3 -> "fan_only"
  - C_POWER=1 + C_MODE=4 -> "dry"
  - C_POWER=1 + C_MODE=6 -> "auto"
  - 缺字段 -> None
And 移除 _build_ha_climate_preview 里的"模式枚举尚未确认"占位 note
And 新增 note：标注 C_ELECHEATING 控制路径未实测
```

## 目标

为 `_normalize_air_conditioner_status` 的 hvac_mode 推断增强写失败测试。`_normalize_air_conditioner_status` 在 `client.py`，需要扩展它。

## 待创建/修改

- 扩展 `tests/test_client.py`（追加测试函数即可，单测直接构造 `SuningSmartHomeClient` 实例并调 `_normalize_air_conditioner_status`）
- `client.py` 暂不实现增强（Red）

## 测试要点

构造 device dict，verify 增强后：

1. `{"status": {"C_POWER": "0"}}` → `hvac_mode == "off"`
2. `{"status": {"C_POWER": "1", "C_MODE": "1"}}` → `hvac_mode == "cool"`
3. `{"status": {"C_POWER": "1", "C_MODE": "2"}}` → `"heat"`
4. `{"status": {"C_POWER": "1", "C_MODE": "3"}}` → `"fan_only"`
5. `{"status": {"C_POWER": "1", "C_MODE": "4"}}` → `"dry"`
6. `{"status": {"C_POWER": "1", "C_MODE": "6"}}` → `"auto"`
7. `{"status": {"SN_POWER": "1", "SN_MODE": "1"}}`（无 C_ 字段）→ 同样推断为 `"cool"`
8. `{"status": {}}` → `hvac_mode is None`
9. `{"status": {"C_POWER": "1"}}` 但 C_MODE 缺失 → `hvac_mode is None`（**不**默认 auto）
10. `ha_climate_preview.notes` 不再含 `"模式枚举尚未确认"` 这段文字
11. `ha_climate_preview.notes` 含 `"C_ELECHEATING"` 这段文字

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_client.py -x -q -k "normalize or hvac_mode"
```

**预期**：FAIL。
