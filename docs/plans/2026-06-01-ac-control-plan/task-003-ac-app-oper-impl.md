# Task 003 Impl: app_oper 通用方法实现 (Green)

**depends-on**: task-003-ac-app-oper-test.md

## BDD Scenario

```
Scenario: 发送单个命令成功 / 一次发送多个命令 / 业务错误 / 未登录重引导 / 字段值类型校验
```

## 目标

在 `ac_control.py` 实现 `app_oper`，让测试通过。

## 待创建/修改

- **新建** `src/xiaobiu/ac_control.py`：
  - `APP_OPER_URL = "https://itapig.suning.com/api/trade/shsys/appOper"`
  - `def _stringify_cmd_values(cmd: Mapping[str, Any]) -> dict[str, str]`：把所有 value 转 `str`（int/float 走 `str(value)`）。注意温度用 `str(value)` 即可：`24.0` → `"24.0"`，`24` → `"24"`；这是当前实现。
  - `def build_app_oper_body(device_id: str, model_id: str, cmd: Mapping[str, Any]) -> str`：返回紧凑 JSON 字符串。`{"deviceId", "modelId", "cmd"}`，cmd 是 `json.dumps(_stringify_cmd_values(cmd), separators=(",", ":"), ensure_ascii=False)`。
  - `def app_oper(client, device_id: str, model_id: str, cmd: Mapping[str, Any]) -> dict[str, Any]`：
    1. `body = build_app_oper_body(...)`
    2. `response = client._request_app_api(APP_OPER_URL, body=body)`
    3. `data = response.json()`
    4. `if data.get("responseCode") != "0": raise SuningError(data.get("responseMsg") or "appOper failed")`
    5. `return data`
  - 引入 `from .client import SuningError`（避免循环导入：把 SuningError 留在 client.py，从 ac_control 引用；或把 SuningError 提取到一个新 exceptions 模块——本任务用前者保持改动最小）。

## 实现注意点

- 不要 import `SuningSmartHomeClient`（避免循环）。duck-type 即可。
- `_request_app_api` 已有未登录重引导逻辑（`client.py:635-640`），app_oper 走它就行。
- 测试中"未登录重引导"场景已在 `_request_app_api` 自身的测试覆盖；本任务测试可省略（_request_app_api 是依赖项）。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "app_oper"
```

**预期**：PASS。
