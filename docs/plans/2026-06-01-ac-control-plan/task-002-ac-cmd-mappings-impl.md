# Task 002 Impl: 映射表实现 (Green)

**depends-on**: task-002-ac-cmd-mappings-test.md

## BDD Scenario

```
C_FIELD_TO_HVAC / C_FIELD_TO_FAN / HVAC_TO_C_FIELD / FAN_TO_C_FIELD
SWING_TO_CMD / PRESET_TO_CMD
```

## 目标

新建 `src/xiaobiu/ac_control.py` 并定义所有映射表。

## 待创建/修改

- **新建** `src/xiaobiu/ac_control.py`：
  - 顶部 `from .models import HvacMode, FanSpeed, SwingMode, PresetMode`
  - 定义 `C_FIELD_TO_HVAC` / `C_FIELD_TO_FAN`
  - 用推导式生成 `HVAC_TO_C_FIELD = {v: k for k, v in C_FIELD_TO_HVAC.items()}` 等反向表
  - `SWING_TO_CMD: dict[SwingMode, dict[str, str]]`
  - `PRESET_TO_CMD`: 推荐结构 `dict[tuple[str, str], tuple[str, str]]` 或者 `dict[PresetMode, dict[str, str]]`，含开/关两侧。例：
    ```python
    PRESET_TO_CMD: dict[str, dict[str, str]] = {
        "eco": {"C_ECO": "1"},
        "fresh_air": {"C_FRESHAIR": "1"},
        "electric_heating": {"C_ELECHEATING": "1"},
    }
    PRESET_OFF_CMD: dict[str, dict[str, str]] = {
        "eco": {"C_ECO": "0"},
        "fresh_air": {"C_FRESHAIR": "0"},
        "electric_heating": {"C_ELECHEATING": "0"},
    }
    ```

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "mapping or swing or preset or hvac or fan"
```

**预期**：PASS。
