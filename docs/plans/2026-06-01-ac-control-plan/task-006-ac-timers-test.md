# Task 006 Test: 定时列表测试 (Red)

**depends-on**: task-002-ac-cmd-mappings-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 3:

```
Scenario: 拉取定时
Given 已登录 client，空调已知
When client.list_device_timers(device_id)
Then 返回 Timer 列表，每项包含 timerName / timer / state / timerCmd
And state == "0" 表示启用、"-1" 表示禁用
And 网络失败时抛 SuningError
```

## 目标

为 `list_device_timers(client, device_id)` 写失败测试。

## 待创建/修改

- 扩展 `tests/test_ac_control.py`
- 暂不实现（Red）

## 测试要点

HAR 中 `queryTimer` 响应：

```json
{
  "responseData": {
    "data": [
      {"timer": "F,00,30,0", "timerName": "关闭时间", "state": "-1", "timerCmd": {"C_POWER": "0"}},
      {"timer": "F,11,40,0", "timerName": "开启时间", "state": "0",  "timerCmd": {"C_POWER": "1"}}
    ]
  },
  "responseCode": "0"
}
```

1. mock `client._request_app_api(QUERY_TIMER_URL, body='{"timerName":"","deviceId":"..."}')` 返回上述结构。
2. 断言返回 list[Timer]，每项：
   - `Timer(name="关闭时间", schedule="F,00,30,0", enabled=False, command={"C_POWER": "0"})`
   - `Timer(name="开启时间", schedule="F,11,40,0", enabled=True,  command={"C_POWER": "1"})`
3. body 中 `deviceId` 等于传入的 device_id。
4. `enabled` 映射规则：`state == "0" -> True`，其他值 `-> False`（与 spec 中 `-1` 一致；保守起见只把 `"0"` 视为启用）。
5. responseCode != "0" → 抛 `SuningError`。
6. `responseData.data` 不是 list → 抛 `SuningError("定时列表格式不正确")`。
7. 单条 item 缺字段 → 抛 `SuningError`。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "timer"
```

**预期**：FAIL。
