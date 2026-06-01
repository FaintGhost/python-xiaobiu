# 空调控制 Plan — _index

> 来源设计：`docs/plans/2026-06-01-ac-control-design/bdd-specs.md`
> 目标：在 `python-xiaobiu` 中实现苏宁空调的完整状态获取 + 控制 API + CLI。
> 工作流：Test-First（Red-Green），每对 test/impl 任务共享 NN 前缀。

## 约束

- 测试覆盖率 ≥ 80%（仅新增代码）。
- HTTP 一律用 `unittest.mock` 隔离，禁止打真实网络。
- `cmd` 字段必须以**紧凑 JSON 字符串**发送（无空格），且所有 value 序列化为字符串。
- 不重构 `client.py` 主结构，最小改动。
- 命名空间：新模块 `src/xiaobiu/ac_control.py` 承载控制逻辑；`models.py` 追加枚举与新模型；`client.py` 薄薄一层转调。
- 暂不实现 `SN_CLOUD_TIMER` 的写入；只做定时列表查询。

## 架构概览

```
src/xiaobiu/
  ac_control.py   [新] 枚举、映射表、app_oper、高层 API、queryTemplate/queryTimer 解析
  models.py       [+新枚举 + 新模型]
  client.py       [薄改] 转发 + 增强 _normalize_air_conditioner_status 的 hvac_mode 推断
  __init__.py     [+] 导出新枚举和高层 API

tests/
  test_ac_control.py      [新] 覆盖 ac_control.py
  test_client_state.py    [+] _normalize_air_conditioner_status 增强测试
  test_client_cli.py      [+] CLI 新子命令解析
  test_models.py          [新] 新枚举与新模型

README.md          [+] 控制示例 + C_ELECHEATING 标注
```

## 任务清单（按 Red→Green 顺序）

| NN | Feature | Type | File |
|----|---------|------|------|
| 001 | ac-enums | test | `task-001-ac-enums-test.md` |
| 001 | ac-enums | impl | `task-001-ac-enums-impl.md` |
| 002 | ac-cmd-mappings | test | `task-002-ac-cmd-mappings-test.md` |
| 002 | ac-cmd-mappings | impl | `task-002-ac-cmd-mappings-impl.md` |
| 003 | ac-app-oper | test | `task-003-ac-app-oper-test.md` |
| 003 | ac-app-oper | impl | `task-003-ac-app-oper-impl.md` |
| 004 | ac-highlevel | test | `task-004-ac-highlevel-test.md` |
| 004 | ac-highlevel | impl | `task-004-ac-highlevel-impl.md` |
| 005 | ac-panel-template | test | `task-005-ac-panel-template-test.md` |
| 005 | ac-panel-template | impl | `task-005-ac-panel-template-impl.md` |
| 006 | ac-timers | test | `task-006-ac-timers-test.md` |
| 006 | ac-timers | impl | `task-006-ac-timers-impl.md` |
| 007 | ac-state-hvac | test | `task-007-ac-state-hvac-test.md` |
| 007 | ac-state-hvac | impl | `task-007-ac-state-hvac-impl.md` |
| 008 | cli-ac-control | test | `task-008-cli-ac-control-test.md` |
| 008 | cli-ac-control | impl | `task-008-cli-ac-control-impl.md` |
| 009 | docs-readme | impl | `task-009-docs-readme-impl.md` |

## 执行 Plan

- [Task 001 Test: 枚举测试 (Red)](./task-001-ac-enums-test.md)
- [Task 001 Impl: 枚举实现 (Green)](./task-001-ac-enums-impl.md)
- [Task 002 Test: 映射表测试 (Red)](./task-002-ac-cmd-mappings-test.md)
- [Task 002 Impl: 映射表实现 (Green)](./task-002-ac-cmd-mappings-impl.md)
- [Task 003 Test: app_oper 测试 (Red)](./task-003-ac-app-oper-test.md)
- [Task 003 Impl: app_oper 实现 (Green)](./task-003-ac-app-oper-impl.md)
- [Task 004 Test: 高层 API 测试 (Red)](./task-004-ac-highlevel-test.md)
- [Task 004 Impl: 高层 API 实现 (Green)](./task-004-ac-highlevel-impl.md)
- [Task 005 Test: panel template 测试 (Red)](./task-005-ac-panel-template-test.md)
- [Task 005 Impl: panel template 实现 (Green)](./task-005-ac-panel-template-impl.md)
- [Task 006 Test: timers 测试 (Red)](./task-006-ac-timers-test.md)
- [Task 006 Impl: timers 实现 (Green)](./task-006-ac-timers-impl.md)
- [Task 007 Test: 状态 hvac_mode 推断测试 (Red)](./task-007-ac-state-hvac-test.md)
- [Task 007 Impl: 状态 hvac_mode 推断实现 (Green)](./task-007-ac-state-hvac-impl.md)
- [Task 008 Test: CLI 解析测试 (Red)](./task-008-cli-ac-control-test.md)
- [Task 008 Impl: CLI 子命令实现 (Green)](./task-008-cli-ac-control-impl.md)
- [Task 009 Impl: README 更新](./task-009-docs-readme-impl.md)

## 验证

- 每对 test/impl 任务完成后执行 `uv run pytest tests/ -x -q`，确认相关测试通过、且未破坏既有测试。
- 最终一轮执行 `uv run pytest tests/ --cov=xiaobiu --cov-report=term-missing`，要求新增行覆盖 ≥ 80%。
- CLI 烟测：`uv run xiaobiucli control --help`、`set-mode --help` 等输出与设计一致。
