# Task 005 Impl: 面板模板解析实现 (Green)

**depends-on**: task-005-ac-panel-template-test.md

## BDD Scenario

```
Scenario: 解析 queryTemplate 字段集
```

## 目标

在 `ac_control.py` 实现面板模板解析。

## 待创建/修改

- 追加 `src/xiaobiu/ac_control.py`：
  - `PANEL_QUERY_URL = "https://shcss.suning.com/shcss-web/api/panel/queryTemplate.do"`
  - `def parse_panel_components(containers: Sequence[Mapping[str, Any]]) -> list[str] | None`：
    - 遍历每个 container，读 `component` 字符串
    - `try json.loads(component) except JSONDecodeError: return None`
    - 若不是 list：return None
    - 遍历 dict，把 value 用 `","` split，每项 `.strip()`，跳过空
    - 收集到 `set`
    - 返回 sorted list
  - `def get_device_panel_template(client, device_id: str, model_id: str, *, category_id: str = "0002") -> PanelTemplate | None`：
    - 拼 URL
    - `response = client.session.get(url, timeout=client.timeout)`
    - `response.raise_for_status()`
    - `data = response.json()`
    - 若 `data.get("code") != "0"`：return None
    - `containers = (data.get("data") or {}).get("containers") or []`
    - `components = parse_panel_components(containers)`
    - 若 components is None：return None
    - 返回 `PanelTemplate(device_id=device_id, model_id=model_id, components=components)`
    - 任何异常（请求失败/JSON 失败）降级为 return None

## 验证

```bash
cd /root/workspace/python-xiaobiu
uv run pytest tests/test_ac_control.py -x -q -k "panel"
```

**预期**：PASS。
