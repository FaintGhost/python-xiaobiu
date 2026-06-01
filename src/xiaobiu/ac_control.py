"""Air conditioner control surface (commands, mappings, helpers).

The control protocol speaks a flat dictionary of ``C_*`` keys (and a few
``SN_*`` legacy keys) where every value is a string.  ``cmd`` itself is
serialised as a *compact* JSON string and shipped in a single
``appOper`` request.  This module is the source of truth for the field
set, the enum ↔ raw value mapping, and the higher-level helpers that
the client uses to build requests.

The functions take a ``client`` parameter by duck type: they only
require ``client._request_app_api(url, body=...)`` to exist, which is
true for :class:`xiaobiu.SuningSmartHomeClient`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from .client import SuningError
from .models import (
  FanSpeed,
  HvacMode,
  PanelTemplate,
  PresetMode,
  SwingMode,
  Timer,
)

if TYPE_CHECKING:  # pragma: no cover - only for type hints
  pass


APP_OPER_URL = "https://itapig.suning.com/api/trade/shsys/appOper"
QUERY_TIMER_URL = "https://itapig.suning.com/api/trade/shsys/queryTimer"
PANEL_QUERY_URL = "https://shcss.suning.com/shcss-web/api/panel/queryTemplate.do"

TEMP_MIN_C = 16.0
TEMP_MAX_C = 32.0

C_FIELD_TO_HVAC: dict[str, HvacMode] = {
  "1": HvacMode.COOL,
  "2": HvacMode.HEAT,
  "3": HvacMode.FAN_ONLY,
  "4": HvacMode.DRY,
  "6": HvacMode.AUTO,
}

C_FIELD_TO_FAN: dict[str, FanSpeed] = {
  "0": FanSpeed.AUTO,
  "1": FanSpeed.LOW,
  "2": FanSpeed.MID,
  "3": FanSpeed.HIGH,
  "4": FanSpeed.HIGHER,
  "5": FanSpeed.HIGHEST,
}

HVAC_TO_C_FIELD: dict[HvacMode, str] = {mode: raw for raw, mode in C_FIELD_TO_HVAC.items()}
FAN_TO_C_FIELD: dict[FanSpeed, str] = {speed: raw for raw, speed in C_FIELD_TO_FAN.items()}

SWING_TO_CMD: dict[SwingMode, dict[str, str]] = {
  SwingMode.OFF: {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "0"},
  SwingMode.VERTICAL: {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "0"},
  SwingMode.HORIZONTAL: {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "1"},
  SwingMode.BOTH: {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "1"},
}

PRESET_ON_CMD: dict[PresetMode, dict[str, str]] = {
  PresetMode.ECO: {"C_ECO": "1"},
  PresetMode.FRESH_AIR: {"C_FRESHAIR": "1"},
}

PRESET_OFF_CMD: dict[PresetMode, dict[str, str]] = {
  PresetMode.ECO: {"C_ECO": "0"},
  PresetMode.FRESH_AIR: {"C_FRESHAIR": "0"},
}


def _stringify_cmd_values(cmd: Mapping[str, Any]) -> dict[str, str]:
  """Coerce every cmd value to ``str`` so the wire format is consistent."""

  return {key: str(value) for key, value in cmd.items()}


def build_app_oper_body(device_id: str, model_id: str, cmd: Mapping[str, Any]) -> str:
  """Build the compact JSON body the ``appOper`` endpoint expects."""

  cmd_str = json.dumps(
    _stringify_cmd_values(cmd),
    separators=(",", ":"),
    ensure_ascii=False,
  )
  return json.dumps(
    {"deviceId": device_id, "modelId": model_id, "cmd": cmd_str},
    separators=(",", ":"),
    ensure_ascii=False,
  )


def app_oper(
  client: Any,
  device_id: str,
  model_id: str,
  cmd: Mapping[str, Any],
) -> dict[str, Any]:
  """Send a single ``appOper`` command and return the decoded response.

  Network/HTTP plumbing is delegated to ``client._request_app_api`` so
  the gsSign / snTraceId bootstrap and the auto-relogin on a redirect
  are inherited for free.  ``SuningError`` is raised when the response
  carries a non-zero ``responseCode``.
  """

  body = build_app_oper_body(device_id, model_id, cmd)
  response = client._request_app_api(APP_OPER_URL, body=body)
  try:
    data = response.json()
  except ValueError as error:
    raise SuningError(f"appOper 返回了无法解析的 JSON 响应: {error}") from error
  if str(data.get("responseCode") or "") != "0":
    raise SuningError(data.get("responseMsg") or "appOper 调用失败")
  return data


def parse_panel_components(
  containers: Sequence[Mapping[str, Any]],
) -> list[str] | None:
  """Flatten the ``containers[].component`` field set into a sorted list.

  Each ``component`` value is a JSON-stringified list of
  ``{COM_POWER: C_POWER, COM_STATE: C_MODE,C_FANSPEED,...}`` style
  objects.  We merge all value strings, split on ``,`` and return the
  unique sorted field names.  Any structural problem collapses the
  result to ``None`` so the caller can degrade gracefully.
  """

  if containers is None:
    return None
  fields: set[str] = set()
  for container in containers:
    raw = container.get("component") if isinstance(container, Mapping) else None
    if not isinstance(raw, str) or not raw:
      continue
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError:
      return None
    if not isinstance(parsed, list):
      return None
    for entry in parsed:
      if not isinstance(entry, Mapping):
        return None
      for value in entry.values():
        if not isinstance(value, str):
          return None
        for piece in value.split(","):
          cleaned = piece.strip()
          if cleaned:
            fields.add(cleaned)
  if not fields:
    return None
  return sorted(fields)


def get_device_panel_template(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  category_id: str = "0002",
) -> PanelTemplate | None:
  """Fetch the runtime panel template for ``device_id``.

  Returns ``None`` on any failure (HTTP error, malformed JSON, code != 0)
  so the caller can keep going on a partial response.
  """

  query = (
    f"{PANEL_QUERY_URL}"
    f"?deviceId={device_id}&modelId={model_id}&categoryId={category_id}"
  )
  try:
    response = client.session.get(query, timeout=client.timeout)
    response.raise_for_status()
    payload = response.json()
  except Exception:
    return None
  if not isinstance(payload, Mapping) or str(payload.get("code") or "") != "0":
    return None
  data_block = payload.get("data") or {}
  if not isinstance(data_block, Mapping):
    return None
  containers = data_block.get("containers") or []
  components = parse_panel_components(containers)
  if components is None:
    return None
  return PanelTemplate(
    device_id=device_id,
    model_id=model_id,
    components=components,
  )


def list_device_timers(client: Any, device_id: str) -> list[Timer]:
  """Fetch the cloud timer list for ``device_id``.

  Enabled state is mapped from ``state == "0"``; any other value is
  treated as disabled (per the HAR the device returns ``"-1"`` for
  disabled entries).
  """

  body = json.dumps(
    {"timerName": "", "deviceId": device_id},
    separators=(",", ":"),
    ensure_ascii=False,
  )
  response = client._request_app_api(QUERY_TIMER_URL, body=body)
  try:
    payload = response.json()
  except ValueError as error:
    raise SuningError(f"queryTimer 返回了无法解析的 JSON 响应: {error}") from error
  if str(payload.get("responseCode") or "") != "0":
    raise SuningError(payload.get("responseMsg") or "queryTimer 调用失败")
  response_data = payload.get("responseData") or {}
  if not isinstance(response_data, Mapping):
    raise SuningError("定时列表格式不正确。")
  items = response_data.get("data")
  if not isinstance(items, list):
    raise SuningError("定时列表格式不正确，缺少 data 数组。")
  timers: list[Timer] = []
  for item in items:
    if not isinstance(item, Mapping):
      raise SuningError("定时列表项格式不正确。")
    timers.append(
      Timer(
        name=str(item.get("timerName") or ""),
        schedule=str(item.get("timer") or ""),
        enabled=str(item.get("state") or "") == "0",
        command={str(k): str(v) for k, v in (item.get("timerCmd") or {}).items()},
      )
    )
  return timers


def infer_hvac_mode(*, power_on: bool | None, mode_raw: Any) -> HvacMode | None:
  """Translate raw status fields into a typed HVAC mode.

  ``power_on is False`` always wins and yields ``HvacMode.OFF``; only an
  explicitly powered-on device is mapped to a running mode.  Unknown
  mode values (e.g. HAR has not exposed ``C_MODE=5``) collapse to
  ``None`` so the caller can render an ``unavailable`` preview.
  """

  if power_on is False:
    return HvacMode.OFF
  if power_on is not True:
    return None
  if mode_raw is None:
    return None
  return C_FIELD_TO_HVAC.get(str(mode_raw).strip())


def infer_fan_speed(speed_raw: Any) -> FanSpeed | None:
  """Translate a raw fan speed value into a typed :class:`FanSpeed`."""

  if speed_raw is None:
    return None
  return C_FIELD_TO_FAN.get(str(speed_raw).strip())


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------


def _validate_temperature(value: float) -> float:
  if not (TEMP_MIN_C <= value <= TEMP_MAX_C):
    raise ValueError(
      f"target temperature {value} out of range [{TEMP_MIN_C}, {TEMP_MAX_C}]",
    )
  return round(float(value), 1)


def turn_on(client: Any, device_id: str, model_id: str) -> dict[str, Any]:
  return app_oper(client, device_id, model_id, {"C_POWER": "1"})


def turn_off(client: Any, device_id: str, model_id: str) -> dict[str, Any]:
  return app_oper(client, device_id, model_id, {"C_POWER": "0"})


def set_hvac_mode(
  client: Any,
  device_id: str,
  model_id: str,
  mode: HvacMode,
) -> dict[str, Any]:
  if mode is HvacMode.OFF:
    return turn_off(client, device_id, model_id)
  if mode not in HVAC_TO_C_FIELD:
    raise SuningError(f"unsupported hvac mode: {mode!r}")
  return app_oper(client, device_id, model_id, {"C_MODE": HVAC_TO_C_FIELD[mode]})


def set_temperature(
  client: Any,
  device_id: str,
  model_id: str,
  value: float,
) -> dict[str, Any]:
  try:
    numeric = float(value)
  except (TypeError, ValueError) as error:
    raise ValueError(f"target temperature must be numeric, got {value!r}") from error
  validated = _validate_temperature(numeric)
  return app_oper(client, device_id, model_id, {"C_TEMPERATURE": str(validated)})


def set_fan_mode(
  client: Any,
  device_id: str,
  model_id: str,
  speed: FanSpeed,
) -> dict[str, Any]:
  if speed not in FAN_TO_C_FIELD:
    raise SuningError(f"unsupported fan speed: {speed!r}")
  return app_oper(client, device_id, model_id, {"C_FANSPEED": FAN_TO_C_FIELD[speed]})


def set_swing_mode(
  client: Any,
  device_id: str,
  model_id: str,
  swing: SwingMode,
) -> dict[str, Any]:
  if swing not in SWING_TO_CMD:
    raise SuningError(f"unsupported swing mode: {swing!r}")
  return app_oper(client, device_id, model_id, SWING_TO_CMD[swing])


_PRESET_NONE_OFF: dict[str, str] = {
  "C_ECO": "0",
  "C_FRESHAIR": "0",
  "C_ELECHEATING": "0",
}


def set_preset_mode(
  client: Any,
  device_id: str,
  model_id: str,
  preset: PresetMode,
) -> dict[str, Any]:
  if preset is PresetMode.NONE:
    return app_oper(client, device_id, model_id, _PRESET_NONE_OFF)
  if preset in PRESET_ON_CMD:
    return app_oper(client, device_id, model_id, PRESET_ON_CMD[preset])
  raise SuningError(f"unsupported preset mode: {preset!r}")


def set_electric_heating(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
) -> dict[str, Any]:
  # C_ELECHEATING was surfaced by queryTemplate but the control path
  # was not exercised in the 2026-06-01 HAR; treat with care.
  return app_oper(
    client,
    device_id,
    model_id,
    {"C_ELECHEATING": "1" if on else "0"},
  )


__all__ = [
  "APP_OPER_URL",
  "C_FIELD_TO_FAN",
  "C_FIELD_TO_HVAC",
  "FAN_TO_C_FIELD",
  "HVAC_TO_C_FIELD",
  "PANEL_QUERY_URL",
  "PRESET_OFF_CMD",
  "PRESET_ON_CMD",
  "PanelTemplate",
  "QUERY_TIMER_URL",
  "SWING_TO_CMD",
  "TEMP_MAX_C",
  "TEMP_MIN_C",
  "Timer",
  "app_oper",
  "build_app_oper_body",
  "get_device_panel_template",
  "infer_fan_speed",
  "infer_hvac_mode",
  "list_device_timers",
  "parse_panel_components",
  "set_electric_heating",
  "set_fan_mode",
  "set_hvac_mode",
  "set_preset_mode",
  "set_swing_mode",
  "set_temperature",
  "turn_off",
  "turn_on",
]
