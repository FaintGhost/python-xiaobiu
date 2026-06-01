# 空调控制对齐 HA — _index

> 来源设计：`docs/plans/2026-06-02-ac-control-align-ha-design/bdd-specs.md`
> 目标：把 FanSpeed 改名对齐 HA climate、HvacMode 加 QUICK、摆风/预设拆成独立 setter、新增 5 个 CLI 子命令。

## 约束

- 全部新代码测试覆盖率 ≥ 80%。
- `set_aux_heat(on=True)` 在非制热时抛 `SuningError`。
- 旧 `set_preset_mode(PresetMode.NONE)` 不再"一键关全部"——它现在只对应 PresetMode.NONE 自身的 on-cmd。
- 不重写 `keep_alive` / 登录 / session。

## 任务清单

| NN | Feature | Type | File |
|----|---------|------|------|
| 010 | fan-speed-rename | test | `task-010-fan-speed-rename-test.md` |
| 010 | fan-speed-rename | impl | `task-010-fan-speed-rename-impl.md` |
| 011 | hvac-mode-quick | test | `task-011-hvac-mode-quick-test.md` |
| 011 | hvac-mode-quick | impl | `task-011-hvac-mode-quick-impl.md` |
| 012 | swing-independent | test | `task-012-swing-independent-test.md` |
| 012 | swing-independent | impl | `task-012-swing-independent-impl.md` |
| 013 | preset-independent | test | `task-013-preset-independent-test.md` |
| 013 | preset-independent | impl | `task-013-preset-independent-impl.md` |
| 014 | aux-heat-precheck | test | `task-014-aux-heat-precheck-test.md` |
| 014 | aux-heat-precheck | impl | `task-014-aux-heat-precheck-impl.md` |
| 015 | client-wrappers | impl | `task-015-client-wrappers-impl.md` |
| 016 | cli-subcommands | test | `task-016-cli-subcommands-test.md` |
| 016 | cli-subcommands | impl | `task-016-cli-subcommands-impl.md` |
| 017 | docs-readme | impl | `task-017-docs-readme-impl.md` |
| 018 | final-verify | impl | `task-018-final-verify-impl.md` |

## 执行 Plan

- [Task 010 Test: FanSpeed 改名测试 (Red)](./task-010-fan-speed-rename-test.md)
- [Task 010 Impl: FanSpeed 改名实现 (Green)](./task-010-fan-speed-rename-impl.md)
- [Task 011 Test: QUICK 模式测试 (Red)](./task-011-hvac-mode-quick-test.md)
- [Task 011 Impl: QUICK 模式实现 (Green)](./task-011-hvac-mode-quick-impl.md)
- [Task 012 Test: 摆风独立测试 (Red)](./task-012-swing-independent-test.md)
- [Task 012 Impl: 摆风独立实现 (Green)](./task-012-swing-independent-impl.md)
- [Task 013 Test: 预设独立测试 (Red)](./task-013-preset-independent-test.md)
- [Task 013 Impl: 预设独立实现 (Green)](./task-013-preset-independent-impl.md)
- [Task 014 Test: 电辅热前置测试 (Red)](./task-014-aux-heat-precheck-test.md)
- [Task 014 Impl: 电辅热前置实现 (Green)](./task-014-aux-heat-precheck-impl.md)
- [Task 015 Impl: client 薄包装方法](./task-015-client-wrappers-impl.md)
- [Task 016 Test: CLI 子命令测试 (Red)](./task-016-cli-subcommands-test.md)
- [Task 016 Impl: CLI 子命令实现 (Green)](./task-016-cli-subcommands-impl.md)
- [Task 017 Impl: README 更新](./task-017-docs-readme-impl.md)
- [Task 018 Impl: 最终验证 + commit](./task-018-final-verify-impl.md)

## 验证

- 每对 test/impl 完成后 `cd /root/workspace/python-xiaobiu && /root/workspace/python-xiaobiu/.venv/bin/python -m pytest tests/ -q` 全绿
- 最终 `pytest tests/ --cov=xiaobiu --cov-report=term-missing` 新增覆盖 ≥ 80%
- 真实设备验证：用户跑 `xiaobiucli set-fan --speed turbo`、`set-vertical-swing --off` 等命令确认

## 批次执行

- **Batch 8** (T010-T014, test+impl)：5 对 Red→Green，5 个枚举/setter 改造
- **Batch 9** (T015-T017, impl/test/impl)：client 薄包装 + CLI + README
- **Batch 10** (T018)：最终验证 + commit
