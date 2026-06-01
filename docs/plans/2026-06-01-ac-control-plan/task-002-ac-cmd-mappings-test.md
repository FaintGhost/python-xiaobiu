# Task 002 Test: 映射表测试 (Red)

**depends-on**: task-001-ac-enums-impl.md（需要枚举类型已存在）

## BDD Scenario

来自 bdd-specs.md Feature 5:

```
在 xiaobiu/ac_control.py（或新模块）定义：
  C_FIELD_TO_HVAC: dict[str, HvacMode] = {"1": COOL, "2": HEAT, "3": FAN_ONLY, "4": DRY, "6": AUTO}
  C_FIELD_TO_FAN: dict[str, FanSpeed]  = {"0": AUTO, "1": LOW, "2": MID, "3": HIGH, "4": HIGHER, "5": HIGHEST}
  HVAC_TO_C_FIELD / FAN_TO_C_FIELD 反向表
  SWING_TO_CMD: dict[SwingMode, dict[str,str]]
  PRESET_TO_CMD: dict[str, tuple[str,str]]  # preset -> (field, value)
```

## 目标

为 C_FIELD ↔ 枚举的映射、SWING/PRESET 的 cmd 字典映射写失败测试。

## 待创建/修改

- **新建** `tests/test_ac_control.py`
- 暂不创建 `src/xiaobiu/ac_control.py`（**不实现**）

## 测试要点

1. `C_FIELD_TO_HVAC`:
   - `C_FIELD_TO_HVAC["1"] is HvacMode.COOL`
   - `C_FIELD_TO_HVAC["2"] is HvacMode.HEAT`
   - `C_FIELD_TO_HVAC["3"] is HvacMode.FAN_ONLY`
   - `C_FIELD_TO_HVAC["4"] is HvacMode.DRY`
   - `C_FIELD_TO_HVAC["6"] is HvacMode.AUTO`
   - `len(C_FIELD_TO_HVAC) == 5`（不包含 5）
2. `C_FIELD_TO_FAN`:
   - `"0" -> AUTO`, `"1" -> LOW`, `"2" -> MID`, `"3" -> HIGH`, `"4" -> HIGHER`, `"5" -> HIGHEST`
3. `HVAC_TO_C_FIELD` / `FAN_TO_C_FIELD` 是上述两个表的反向表，且键值互为反函数。
4. `SWING_TO_CMD`:
   - `OFF -> {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "0"}`
   - `VERTICAL -> {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "0"}`
   - `HORIZONTAL -> {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "1"}`
   - `BOTH -> {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "1"}`
5. `PRESET_TO_CMD`:
   - `("eco", ("C_ECO", "1"))` / `("none_eco", ("C_ECO", "0"))`
   - `("fresh_air", ("C_FRESHAIR", "1"))` / `("none_fresh_air", ("C_FRESHAIR", "0"))`
   - 建议用 dict key 为 preset 名（`"eco"`, `"fresh_air"`, `"none"`），value 是 `(field, on_value, off_value)` 三元组或两个 dict。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "mapping or swing or preset or hvac or fan"
```

**预期**：FAIL（ImportError），证明 `ac_control` 模块尚未创建。
