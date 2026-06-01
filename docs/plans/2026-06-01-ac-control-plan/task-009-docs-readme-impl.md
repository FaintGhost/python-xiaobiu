# Task 009 Impl: README 更新

**depends-on**: task-008-cli-ac-control-impl.md

## 目标

更新 `README.md`，加入控制示例 + 标注 `C_ELECHEATING` 未实测。

## 待修改

- `README.md`：
  1. 在 `## Usage` 后追加 `## Air Conditioner Control` 章节，演示 Python API：
     ```python
     client.turn_on(family_id=37790, device_id="...")
     client.set_hvac_mode(family_id=37790, device_id="...", mode="cool")
     client.set_temperature(family_id=37790, device_id="...", value=24.0)
     client.set_fan_mode(family_id=37790, device_id="...", speed="low")
     client.set_swing_mode(family_id=37790, device_id="...", swing="vertical")
     client.set_preset_mode(family_id=37790, device_id="...", preset="eco")
     client.list_device_timers(family_id=37790, device_id="...")
     template = client.get_device_panel_template(family_id=37790, device_id="...")
     ```
  2. 扩展 `## CLI` 章节，列出 8 个新子命令。
  3. 新增 `## Notes` 章节：
     - `C_ELECHEATING` 控制路径仅从 queryTemplate 推断，**未在真实设备上抓包验证**，请审慎使用。
     - `SN_CLOUD_TIMER` 的写入控制暂未实现，本版本只读取定时列表。

## 验证

```bash
cd /root/workspace/python-xiaobiu
# 1. README 中 4 个目标短语均存在
grep -q "## Air Conditioner Control" README.md
grep -q "C_ELECHEATING" README.md
grep -q "list_device_timers" README.md
grep -q "set-preset" README.md
echo OK
```

**预期**：所有 `grep -q` 命中，打印 `OK`。
