# 空调状态获取与控制 — BDD Specs

> 来源 HAR：`192.168.1.103_2026_06_01_23_24_28.har`
> 设备 ID：`000165f9b029afa2e5d8`，modelId：`0001000200150000`
> 设计目标：在已有 `list_devices / get_air_conditioner_status` 基础上，补齐面板模板查询、定时查询、设备控制（appOper），并扩展 CLI。

## 关键事实（来源 HAR，已在浏览器抓包验证）

### 控制端点

```
POST https://itapig.suning.com/api/trade/shsys/appOper
Content-Type: application/json
Headers: gsSign / snTraceId / requestTime / terminalType 等（与现有 _request_app_api 一致）

Request body:
{
  "deviceId": "<deviceId>",
  "modelId":  "<modelId>",
  "cmd":      "<JSON 字符串，键为 C_ 字段>"
}

Response (成功):
{
  "responseCode": "0",
  "responseData": { "code": "0", "time": "2026-06-01 23:23:18" }
}
```

`cmd` 字段全集（HAR 实测 + queryTemplate 声明）：

| 字段 | 含义 | 已验证取值 | 备注 |
|------|------|-----------|------|
| `C_POWER` | 电源 | `"0"` 关 / `"1"` 开 | |
| `C_MODE` | 模式 | `1` 制冷 / `2` 制热 / `3` 送风 / `4` 除湿 / `6` 自动 | 缺 `5`（HAR 未验证） |
| `C_TEMPERATURE` | 目标温度 | `"23.0"` ~ `"24.1"` | 字符串、保留 1 位小数 |
| `C_FANSPEED` | 风速 | `0` 自动 / `1` `2` `3` `4` `5` 递增 | |
| `C_AIRVERTICAL` | 上下扫风 | `"0"` 关 / `"1"` 开 | |
| `C_AIRHORIZONTAL` | 左右扫风 | `"0"` 关 / `"1"` 开 | |
| `C_ECO` | ECO | `"1"` 开（HAR）；`"0"` 关（推断） | |
| `C_FRESHAIR` | 新风 | `"0"` 关（HAR）；`"1"` 开（推断） | |
| `C_ELECHEATING` | 电加热 | **HAR 未抓** | 字段名见 queryTemplate，需保留接口、文档标注"未实测" |
| `SN_CLOUD_TIMER` | 云端定时 | **未抓控制** | 定时列表走 `queryTimer` 端点 |

### 其它端点

- `GET https://shcss.suning.com/shcss-web/api/panel/queryTemplate.do?deviceId=...&categoryId=...&modelId=...`
  返回面板字段集（用 `containers[].component` 提取），用于"运行期字段探测"（运行时确认该设备支持哪些字段）。
- `POST https://itapig.suning.com/api/trade/shsys/queryTimer`
  body `{"timerName":"","deviceId":"..."}`，返回定时列表（开启/关闭时间）。

---

## BDD Scenarios

### Feature 1: 设备控制（appOper 通用方法）

#### Scenario: 发送单个命令成功
```
Given 已登录的 SuningSmartHomeClient
And 已知一台空调 deviceId="000165f9b029afa2e5d8"、modelId="0001000200150000"
When 调用 client.app_oper(device_id, model_id, {"C_POWER": "1"})
Then 返回的字典 responseCode == "0"
And responseData.code == "0"
And 内部使用了 _request_app_api（带 gsSign / snTraceId / requestTime）
```

#### Scenario: 一次发送多个命令
```
Given 已登录 client
When 调用 client.app_oper(device_id, model_id, {"C_TEMPERATURE": "24.0", "C_FANSPEED": "2"})
Then cmd 字段被序列化为 '{"C_TEMPERATURE":"24.0","C_FANSPEED":"2"}'（紧凑 JSON，无空格）
And responseCode == "0"
```

#### Scenario: 服务端返回业务错误
```
Given 已登录 client
When 调用 client.app_oper 后，HTTP 200 但 responseCode == "1"
Then 抛出 SuningError，且 message == responseMsg
```

#### Scenario: 未登录触发重引导
```
Given 已登录 client，但 session 已失效
When 调用 app_oper
Then _request_app_api 内部应触发两次 bootstrap_service 重新登录
And 第二次仍失败则抛 AuthenticationError
```

#### Scenario: 字段值类型校验
```
Given 已登录 client
When 调用 client.app_oper(device_id, model_id, {"C_TEMPERATURE": 24.0})  # 传入非字符串
Then 内部把所有 value 序列化为字符串（"24.0"）
And 发送的 cmd 中也是字符串
```

---

### Feature 2: 空调高层控制 API（强类型封装）

#### Scenario: 开关
```
Given 已登录 client，空调已知
When client.turn_on(device_id) / client.turn_off(device_id)
Then 内部以 {"C_POWER": "1"} / {"C_POWER": "0"} 调用 app_oper
And 返回 app_oper 的原始 dict
```

#### Scenario: 设置 HVAC 模式
```
Given 已登录 client，空调已知
When client.set_hvac_mode(device_id, HvacMode.COOL)
Then 内部发送 {"C_MODE": "1"}
And 支持的模式：COOL/HEAT/FAN_ONLY/DRY/AUTO
When client.set_hvac_mode(device_id, "off")
Then 内部发送 {"C_POWER": "0"}（语义映射：off 即关电源）
```

#### Scenario: 设置目标温度
```
Given 已登录 client，空调已知
When client.set_temperature(device_id, 24.0)
Then 内部发送 {"C_TEMPERATURE": "24.0"}
And 当传入 24 时同样序列化为 "24.0"
And 传入非数字抛出 ValueError
```

#### Scenario: 设置风速
```
Given 已登录 client，空调已知
When client.set_fan_mode(device_id, FanSpeed.AUTO)
Then 内部发送 {"C_FANSPEED": "0"}
And FanSpeed.LOW=1 / MID=2 / HIGH=3 / HIGHER=4 / HIGHEST=5
```

#### Scenario: 设置扫风模式
```
Given 已登录 client，空调已知
When client.set_swing_mode(device_id, SwingMode.OFF)
Then 内部发送 {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "0"}
When client.set_swing_mode(device_id, SwingMode.VERTICAL)
Then 内部发送 {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "0"}
When client.set_swing_mode(device_id, SwingMode.HORIZONTAL)
Then 内部发送 {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "1"}
When client.set_swing_mode(device_id, SwingMode.BOTH)
Then 内部发送 {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "1"}
```

#### Scenario: 预设模式
```
Given 已登录 client，空调已知
When client.set_preset_mode(device_id, "eco")
Then 内部发送 {"C_ECO": "1"}
When client.set_preset_mode(device_id, "none")
Then 内部发送 {"C_ECO": "0"}
When client.set_preset_mode(device_id, "fresh_air")
Then 内部发送 {"C_FRESHAIR": "1"}
When client.set_preset_mode(device_id, "none")  # 关新风
Then 内部发送 {"C_FRESHAIR": "0"}
And set_electric_heating(device_id, on=True/False) 走 {"C_ELECHEATING": "1"/"0"}，但 README 标注"未实测"
```

---

### Feature 3: 状态获取增强

#### Scenario: 解析 queryTemplate 字段集
```
Given 已登录 client，空调已知
When client.get_device_panel_template(device_id)
Then 返回 PanelTemplate 对象，包含 components 列表
And 列表中至少能识别出 COM_POWER（指向 C_POWER）和 COM_STATE（包含 C_MODE/C_FANSPEED/...）
And 解析失败（HTML 改了结构）时降级返回 None，且不抛异常
```

#### Scenario: 拉取定时
```
Given 已登录 client，空调已知
When client.list_device_timers(device_id)
Then 返回 Timer 列表，每项包含 timerName / timer / state / timerCmd
And state == "0" 表示启用、"-1" 表示禁用
And 网络失败时抛 SuningError
```

#### Scenario: AirConditionerStatus 增强
```
Given 拉取到的设备 dict
When 调 _normalize_air_conditioner_status
Then hvac_mode 不再总是 None —— 能根据 C_POWER + C_MODE 推断出
  - C_POWER=0 -> "off"
  - C_POWER=1 + C_MODE=1 -> "cool"
  - C_POWER=1 + C_MODE=2 -> "heat"
  - C_POWER=1 + C_MODE=3 -> "fan_only"
  - C_POWER=1 + C_MODE=4 -> "dry"
  - C_POWER=1 + C_MODE=6 -> "auto"
  - 缺字段 -> None
And 移除 _build_ha_climate_preview 里的"模式枚举尚未确认"占位 note
And 新增 note：标注 C_ELECHEATING 控制路径未实测
```

---

### Feature 4: CLI 扩展

#### Scenario: 子命令注册
```
Given xiaobiucli 已安装
When 运行 xiaobiucli --help
Then 输出中包含以下子命令：
  - control
  - set-mode
  - set-temperature
  - set-fan
  - set-swing
  - set-preset
  - timers
  - panel
```

#### Scenario: control 子命令（最常用）
```
Given 已登录、state-file 存在
When 运行 xiaobiucli control --family-id 37790 --device-id <id> --power off
Then 内部调用 client.turn_off(device_id)
And 打印成功状态
```

#### Scenario: set-mode / set-temperature / set-fan
```
Given 已登录
When xiaobiucli set-mode --family-id ... --device-id ... --mode cool
Then 内部调 set_hvac_mode(COOL)
And 非法 mode 值返回非 0 退出码并提示枚举
```

#### Scenario: set-swing
```
Given 已登录
When xiaobiucli set-swing --family-id ... --device-id ... --mode vertical
Then 内部调 set_swing_mode(SwingMode.VERTICAL)
```

#### Scenario: timers / panel
```
When xiaobiucli timers --family-id ... --device-id ...
Then 打印定时列表 JSON
When xiaobiucli panel --family-id ... --device-id ...
Then 打印面板模板解析结果
```

---

### Feature 5: 模型 & 枚举

#### Scenario: 枚举定义
```
在 xiaobiu/models.py 新增：
  HvacMode: Literal["cool","heat","fan_only","dry","auto","off"]
  FanSpeed: Literal["auto","low","mid","high","higher","highest"]
  SwingMode: Literal["off","vertical","horizontal","both"]
  PresetMode: Literal["none","eco","fresh_air"]

在 xiaobiu/ac_control.py（或新模块）定义：
  C_FIELD_TO_HVAC: dict[str, HvacMode] = {"1": COOL, "2": HEAT, "3": FAN_ONLY, "4": DRY, "6": AUTO}
  C_FIELD_TO_FAN: dict[str, FanSpeed]  = {"0": AUTO, "1": LOW, "2": MID, "3": HIGH, "4": HIGHER, "5": HIGHEST}
  HVAC_TO_C_FIELD / FAN_TO_C_FIELD 反向表
  SWING_TO_CMD: dict[SwingMode, dict[str,str]]
  PRESET_TO_CMD: dict[str, tuple[str,str]]  # preset -> (field, value)
```

---

## 架构决策

1. **新增模块** `src/xiaobiu/ac_control.py`：
   - 包含 `app_oper` 调用、HVAC/Fan/Swing/Preset 枚举互转、强类型高层 API。
   - 不动 `client.py` 已有 `list_devices` / `get_air_conditioner_status` 的状态读取路径。
   - 通过 `SuningSmartHomeClient._request_app_api` 复用鉴权（gsSign/snTraceId）。

2. **client.py 仅做轻量扩展**：
   - `app_oper` 委托到 ac_control 模块
   - `turn_on/turn_off/set_hvac_mode/set_temperature/set_fan_mode/set_swing_mode/set_preset_mode/set_electric_heating/list_device_timers/get_device_panel_template` 全部薄薄一层转调
   - `_normalize_air_conditioner_status` 强化：用新枚举把 hvac_mode 算出来

3. **CLI 拆分**：新子命令集中在 client.py 末尾的 `_build_parser` 中追加即可（不另起模块，避免无意义拆分）。

4. **测试**：
   - 用 `unittest.mock` 隔离 HTTP，所有命令测试都不打真实网络
   - 单独抽 `ac_control.py` 让单测更纯粹（无需构造 client session）
   - 覆盖：枚举映射、cmd 序列化（紧凑 JSON、字符串化、混合 key）、错误响应、未登录重试、CLI 解析

5. **不做的事**：
   - 不实现 `SN_CLOUD_TIMER` 控制（数据模型拉取可做，写入留到后续）
   - 不重构 client.py 拆分（保持改动最小）
   - 不改 `keep_alive` 逻辑

---

## 风险与未决项

- `C_ELECHEATING` 控制值未实测 → 接口先实现，默认 `0/1` 推断，README 标注"未实测"。
- HAR 中 `C_MODE=5` 未出现 → enum 暂不映射，未知值保留为 None + note。
- `cmd` 字段顺序在 HAR 中稳定（按点击顺序），但服务端不要求固定顺序——单测要断言"集合相等"而非"有序"。
