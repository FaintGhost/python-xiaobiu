# Task 008 Impl: CLI 子命令实现 (Green)

**depends-on**: task-008-cli-ac-control-test.md

## BDD Scenario

```
Scenario: 子命令注册 / control / set-mode / set-temperature / set-fan / set-swing / set-preset / timers / panel
```

## 目标

在 `client.py` 的 `_build_parser` 和 `main` 中追加 8 个新子命令；在 `client.py`/`SuningSmartHomeClient` 上追加薄薄一层高层 API（turn_on/turn_off/set_hvac_mode/set_temperature/set_fan_mode/set_swing_mode/set_preset_mode/set_electric_heating/list_device_timers/get_device_panel_template），全部转调 ac_control。

## 待修改

- `src/xiaobiu/client.py`：

  ### `_build_parser` 追加子命令

  ```python
  control = subparsers.add_parser("control")
  add_shared_arguments(control)
  control.add_argument("--family-id", required=True)
  control.add_argument("--device-id", required=True)
  control.add_argument("--power", choices=["on", "off"], required=True)

  set_mode = subparsers.add_parser("set-mode")
  add_shared_arguments(set_mode)
  set_mode.add_argument("--family-id", required=True)
  set_mode.add_argument("--device-id", required=True)
  set_mode.add_argument("--mode", required=True, choices=["off", "cool", "heat", "fan_only", "dry", "auto"])

  set_temp = subparsers.add_parser("set-temperature")
  add_shared_arguments(set_temp)
  set_temp.add_argument("--family-id", required=True)
  set_temp.add_argument("--device-id", required=True)
  set_temp.add_argument("--temperature", type=float, required=True)

  set_fan = subparsers.add_parser("set-fan")
  add_shared_arguments(set_fan)
  set_fan.add_argument("--family-id", required=True)
  set_fan.add_argument("--device-id", required=True)
  set_fan.add_argument("--speed", required=True, choices=["auto", "low", "mid", "high", "higher", "highest"])

  set_swing = subparsers.add_parser("set-swing")
  add_shared_arguments(set_swing)
  set_swing.add_argument("--family-id", required=True)
  set_swing.add_argument("--device-id", required=True)
  set_swing.add_argument("--mode", required=True, choices=["off", "vertical", "horizontal", "both"])

  set_preset = subparsers.add_parser("set-preset")
  add_shared_arguments(set_preset)
  set_preset.add_argument("--family-id", required=True)
  set_preset.add_argument("--device-id", required=True)
  set_preset.add_argument("--preset", required=True, choices=["none", "eco", "fresh_air"])

  timers_cmd = subparsers.add_parser("timers")
  add_shared_arguments(timers_cmd)
  timers_cmd.add_argument("--family-id", required=True)
  timers_cmd.add_argument("--device-id", required=True)

  panel_cmd = subparsers.add_parser("panel")
  add_shared_arguments(panel_cmd)
  panel_cmd.add_argument("--family-id", required=True)
  panel_cmd.add_argument("--device-id", required=True)
  ```

  ### `SuningSmartHomeClient` 追加方法

  全部为薄壳：
  ```python
  def _resolve_device(self, family_id, device_id):
      device = self.get_device(family_id, device_id=device_id)
      return device["id"], device["modelId"]
  ```

  - `turn_on(self, family_id, device_id) -> dict`
  - `turn_off(self, family_id, device_id) -> dict`
  - `set_hvac_mode(self, family_id, device_id, mode) -> dict`
  - `set_temperature(self, family_id, device_id, value) -> dict`
  - `set_fan_mode(self, family_id, device_id, speed) -> dict`
  - `set_swing_mode(self, family_id, device_id, swing) -> dict`
  - `set_preset_mode(self, family_id, device_id, preset) -> dict`
  - `set_electric_heating(self, family_id, device_id, *, on) -> dict`
  - `list_device_timers(self, family_id, device_id) -> list[Timer]`
  - `get_device_panel_template(self, family_id, device_id) -> PanelTemplate | None`
  - `app_oper(self, device_id, model_id, cmd) -> dict`（直接走 ac_control.app_oper）

  所有方法都用 `_resolve_device` 拿到 `device_id, model_id`，再调 ac_control 里的对应纯函数。

  ### `main` 追加分支

  每个新命令的 main 分支：
  ```python
  if args.command == "control":
      payload = client.turn_off(...) if args.power == "off" else client.turn_on(...)
      _print_payload({"status": "ok", "command": "turn_off", "response": payload})
      return 0
  ```

  - `set-mode`: 模式字符串直接传 `set_hvac_mode`
  - `set-temperature`: `value = float(args.temperature)`；捕获 `ValueError` → 友好错误信息，返回 1
  - `set-fan`: speed 字符串 → `set_fan_mode`
  - `set-swing`: mode 字符串 → `set_swing_mode`
  - `set-preset`: preset 字符串 → `set_preset_mode`
  - `timers`: `_print_payload([t.model_dump(mode="json") for t in client.list_device_timers(...)])`
  - `panel`: `_print_payload(client.get_device_panel_template(...).model_dump(mode="json") if ... else None)`

  ### `__init__.py` 导出

  `PanelTemplate` / `Timer` / 4 个枚举类 / `app_oper` 全部加入 `xiaobiu` 顶层导出。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/ -x -q
```

**预期**：所有测试 PASS（008 测试 + 全部既有 + 001-007）。
