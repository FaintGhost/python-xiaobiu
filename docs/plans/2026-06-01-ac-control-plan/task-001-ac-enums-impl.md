# Task 001 Impl: 枚举定义实现 (Green)

**depends-on**: task-001-ac-enums-test.md

## BDD Scenario

```
Scenario: 枚举定义
在 xiaobiu/models.py 新增：
  HvacMode / FanSpeed / SwingMode / PresetMode
  PanelTemplate / Timer
```

## 目标

实现新枚举与新模型，让 001 测试通过。

## 待修改

- `src/xiaobiu/models.py`：
  - 新增 `HvacMode` 类型别名（用 `typing.Literal` 形式），并定义类 `HvacMode`（继承 `str, Enum`）使 Pydantic 校验生效。
  - 同理定义 `FanSpeed` / `SwingMode` / `PresetMode`。
  - 新增 `PanelTemplate(SuningBaseModel)`：`device_id: str` / `model_id: str` / `components: list[str]`。
  - 新增 `Timer(SuningBaseModel)`：`name: str` / `schedule: str` / `enabled: bool` / `command: dict[str, str]`。
  - 不导出 `__all__` 的具体类型在 `__init__.py` 中追加。

- `src/xiaobiu/__init__.py`：把 4 个枚举类、`PanelTemplate`、`Timer` 加入 `__all__`。

## 实现要点

- 用 `class X(str, Enum)` 而非纯 `Literal`，方便在 `model_copy` 中序列化。
- `Literal` 校验通过 Pydantic 自动完成。
- 保留 `extra="ignore"`，对未知字段宽松。
- 不要硬编码业务映射（业务映射在 002 实现）。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_models.py -x -q
```

**预期**：全部 PASS。
