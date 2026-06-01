# Task 008 Test: CLI 子命令解析测试 (Red)

**depends-on**: task-004-ac-highlevel-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 4:

```
Scenario: 子命令注册
When 运行 xiaobiucli --help
Then 输出中包含：control, set-mode, set-temperature, set-fan, set-swing, set-preset, timers, panel

Scenario: control 子命令（最常用）
When xiaobiucli control --family-id 37790 --device-id <id> --power off
Then 内部调用 client.turn_off(device_id)
And 打印成功状态

Scenario: set-mode / set-temperature / set-fan / set-swing / set-preset / timers / panel
...（参数与高层 API 一一对应）
```

## 目标

为新 CLI 子命令写失败测试。

## 待创建/修改

- 扩展 `tests/test_client.py`（复用现有 cli 测试模式）
- `client.py` 暂不实现新子命令（Red）

## 测试要点

1. `parser.parse_args(["control", "--family-id", "37790", "--device-id", "D1", "--power", "off"])` 解析出 `args.command == "control"`、`args.power == "off"`、`args.family_id == "37790"`、`args.device_id == "D1"`。
2. 类似 `set-mode --mode cool`、`set-temperature --temperature 24.0`、`set-fan --speed low`、`set-swing --mode vertical`、`set-preset --preset eco` 均能解析。
3. 非法 `--mode wrong_value` → argparse 报错退出（用 `pytest.raises(SystemExit)`）。
4. `control` 不指定 `--power` → 抛 SystemExit。
5. `set-temperature` 不指定 `--temperature` → 抛 SystemExit。

注意：完整子命令的"调用高层 API"行为留到 impl 阶段测；本任务只测**解析**和**required 参数**校验。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_client.py -x -q -k "parser or cli or subcommand or control or set_mode or set_temperature or set_fan or set_swing or set_preset"
```

**预期**：FAIL（argparse 选择 required 子命令后调用 `parse_args` 会报 unknown args）。
