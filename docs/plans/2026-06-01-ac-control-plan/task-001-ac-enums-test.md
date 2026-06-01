# Task 001 Test: 枚举定义测试 (Red)

**depends-on**: 无

## BDD Scenario

来自 `bdd-specs.md` Feature 5:

```
Scenario: 枚举定义
在 xiaobiu/models.py 新增：
  HvacMode: Literal["cool","heat","fan_only","dry","auto","off"]
  FanSpeed: Literal["auto","low","mid","high","higher","highest"]
  SwingMode: Literal["off","vertical","horizontal","both"]
  PresetMode: Literal["none","eco","fresh_air"]
```

## 目标

为新枚举（HvacMode / FanSpeed / SwingMode / PresetMode）以及 PanelTemplate / Timer 新模型写失败测试（Red）。

## 待创建/修改

- **新建** `tests/test_models.py`
- 修改 `src/xiaobiu/models.py` 暂不需改（**不实现**，只写测试，期望 ImportError 或断言失败）

## 测试要点

1. `HvacMode` 必须是 `Literal["cool","heat","fan_only","dry","auto","off"]` 之一；非成员抛 ValidationError。
2. `FanSpeed` 必须是 `Literal["auto","low","mid","high","higher","highest"]` 之一。
3. `SwingMode` 必须是 `Literal["off","vertical","horizontal","both"]` 之一。
4. `PresetMode` 必须是 `Literal["none","eco","fresh_air"]` 之一。
5. `PanelTemplate` 模型接受 `device_id / model_id / components: list[str]` 字段（components 是从 queryTemplate containers 解析出的扁平字段集，如 `["C_POWER", "C_MODE", "C_FANSPEED", ...]`）。
6. `Timer` 模型接受 `name: str / schedule: str / enabled: bool / command: dict[str,str]` 字段。

## 验证（执行命令）

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_models.py -x -q
```

**预期**：全部测试 FAIL（ImportError 或 AssertionError），证明尚未实现。
