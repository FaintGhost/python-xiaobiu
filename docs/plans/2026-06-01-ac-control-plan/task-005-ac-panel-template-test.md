# Task 005 Test: 面板模板解析测试 (Red)

**depends-on**: task-002-ac-cmd-mappings-impl.md

## BDD Scenario

来自 bdd-specs.md Feature 3:

```
Scenario: 解析 queryTemplate 字段集
Given 已登录 client，空调已知
When client.get_device_panel_template(device_id)
Then 返回 PanelTemplate 对象，包含 components 列表
And 列表中至少能识别出 COM_POWER（指向 C_POWER）和 COM_STATE（包含 C_MODE/C_FANSPEED/...）
And 解析失败（HTML 改了结构）时降级返回 None，且不抛异常
```

## 目标

为 `parse_panel_components(containers)` + `get_device_panel_template(client, device_id)` 写失败测试。

## 待创建/修改

- 扩展 `tests/test_ac_control.py`
- 暂不实现（Red）

## 测试要点

HAR 中 `queryTemplate.do` 返回结构（节选）：

```json
{
  "code": "0",
  "data": {
    "templateId": "PANEL_AC",
    "containers": [
      {
        "containerId": "TOP",
        "component": "[{\"COM_STATE\":\"C_MODE,C_FANSPEED,C_AIRVERTICAL,C_AIRHORIZONTAL,C_ECO,C_FRESHAIR,C_ELECHEATING,SN_CLOUD_TIMER\"},{\"COM_POWER\":\"C_POWER\"}]"
      },
      ...
    ]
  }
}
```

1. `parse_panel_components(containers)`：遍历 containers，从 `component` 字符串（JSON 数组字符串）解析为 list[dict]，把所有 value 用逗号 split 展平成 `set[str]`，返回去重排序后的 list：
   ```python
   ["C_ECO", "C_ELECHEATING", "C_AIRHORIZONTAL", "C_AIRVERTICAL",
    "C_FANSPEED", "C_FRESHAIR", "C_MODE", "C_POWER", "SN_CLOUD_TIMER"]
   ```
2. 解析失败（component 不是合法 JSON / 不是 list / value 不是 string）：降级返回 None，不抛异常。
3. `get_device_panel_template(client, device_id, model_id)`：拼 URL `https://shcss.suning.com/shcss-web/api/panel/queryTemplate.do?deviceId=...&modelId=...&categoryId=0002`；调 `client.session.get(url, timeout=...)`；解析 `data.containers`，调 `parse_panel_components`；返回 `PanelTemplate(device_id, model_id, components)`。
4. HTTP 失败 / data 不存在 → 返回 `None`。
5. 用 mock `client.session.get` 返回 `MagicMock`，`response.json()` 返回上述结构。

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "panel"
```

**预期**：FAIL。
