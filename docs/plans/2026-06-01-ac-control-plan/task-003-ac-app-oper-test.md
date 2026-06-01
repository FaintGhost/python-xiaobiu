# Task 003 Test: app_oper 通用方法测试 (Red)

**depends-on**: task-002-ac-cmd-mappings-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 1：

```
Scenario: 发送单个命令成功
Given 已登录的 SuningSmartHomeClient
And 已知一台空调 deviceId="000165f9b029afa2e5d8"、modelId="0001000200150000"
When 调用 client.app_oper(device_id, model_id, {"C_POWER": "1"})
Then 返回的字典 responseCode == "0"
And responseData.code == "0"
And 内部使用了 _request_app_api（带 gsSign / snTraceId / requestTime）

Scenario: 一次发送多个命令
...
Scenario: 服务端返回业务错误
...
Scenario: 未登录触发重引导
...
Scenario: 字段值类型校验
...
```

## 目标

为 `app_oper` 写失败测试。**不**实现（Red）。

## 待创建/修改

- 扩展 `tests/test_ac_control.py`
- `src/xiaobiu/ac_control.py` 不存在 → ImportError

## 测试要点

构造一个 fake client（不必真实构造 SuningSmartHomeClient），让 `app_oper` 调用方最小依赖：
- **方案 A**：`ac_control.app_oper(client, device_id, model_id, cmd)` 函数签名，让 client duck-typed：需要 `.session` 和 `_build_app_api_headers` 等。
- **方案 B**：在 `client.py` 上加 `app_oper` 方法，内部调 ac_control 里纯函数 `build_app_oper_payload(device_id, model_id, cmd)` 拼出 `body` 和 `url`，然后用 `self._request_app_api(url, body=body)`。

**本任务定方案 A**（更易单测）：在 `ac_control.py` 定义：
- `def app_oper(client, device_id: str, model_id: str, cmd: dict) -> dict`：
  - 把 cmd 内部序列化为紧凑 JSON 字符串 `json.dumps(cmd, separators=(",", ":"), ensure_ascii=False)`
  - 构造 `body = json.dumps({"deviceId": device_id, "modelId": model_id, "cmd": cmd_str}, ...)`
  - 调用 `client._request_app_api(APP_OPER_URL, body=body)`
  - 解码响应：`response.json()`
  - 若 `responseCode != "0"`：抛 `SuningError(responseMsg)`
  - 返回 dict

测试中用 `unittest.mock.MagicMock` 模拟 client：

1. **单字段命令**：mock `_request_app_api` 返回 `{"responseCode": "0", "responseData": {"code": "0", "time": "..."}}`；调 `app_oper(client, "dev", "mod", {"C_POWER": "1"})`；断言 `_request_app_api` 收到的 `body` 是紧凑 JSON，包含 `cmd='{"C_POWER":"1"}'`。
2. **多字段**：cmd 含 `C_TEMPERATURE` 和 `C_FANSPEED`，断言 JSON 中两个键都存在，且 cmd 字符串无空格。
3. **字符串化**：传入 `{"C_TEMPERATURE": 24.0}`（int/float），断言发出的 cmd 字符串中 value 是 `"24.0"`（或至少是 `"24"` 这种字符串，**测试中要明确到底保留 1 位还是 0 位**——按 004 的 set_temperature 决定）。
4. **业务错误**：mock 返回 `{"responseCode": "1", "responseMsg": "device offline"}`；断言抛 `SuningError("device offline")`。
5. **响应数据格式异常**：mock 返回无效 JSON → 抛 `SuningError`。
6. **URL 正确**：断言 `_request_app_api` 第一个位置参数是 `APP_OPER_URL` 常量。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "app_oper"
```

**预期**：FAIL（ImportError or attribute）。
