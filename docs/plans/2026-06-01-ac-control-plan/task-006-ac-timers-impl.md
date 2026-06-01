# Task 006 Impl: 定时列表实现 (Green)

**depends-on**: task-006-ac-timers-test.md

## BDD Scenario

```
Scenario: 拉取定时
```

## 目标

在 `ac_control.py` 实现 `list_device_timers`。

## 待创建/修改

- 追加 `src/xiaobiu/ac_control.py`：
  - `QUERY_TIMER_URL = "https://itapig.suning.com/api/trade/shsys/queryTimer"`
  - `def list_device_timers(client, device_id: str) -> list[Timer]`：
    1. `body = json.dumps({"timerName": "", "deviceId": device_id}, separators=(",", ":"), ensure_ascii=False)`
    2. `response = client._request_app_api(QUERY_TIMER_URL, body=body)`
    3. `data = response.json()`
    4. `if data.get("responseCode") != "0": raise SuningError(data.get("responseMsg") or "queryTimer failed")`
    5. `rd = data.get("responseData") or {}`
    6. `items = rd.get("data")`
    7. `if not isinstance(items, list): raise SuningError("定时列表格式不正确")`
    8. 遍历 items，构造 `Timer(name=item["timerName"], schedule=item["timer"], enabled=(item["state"] == "0"), command=item.get("timerCmd") or {})`
    9. 任何 KeyError / TypeError → 包成 `SuningError`

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "timer"
```

**预期**：PASS。
