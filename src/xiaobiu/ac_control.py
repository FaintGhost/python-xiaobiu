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

from .exceptions import SuningError
from .models import (
  CapabilityField,
  DeviceCapabilities,
  FanSpeed,
  HvacAction,
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

# ---------------------------------------------------------------------------
# Mode mapping tables
# ---------------------------------------------------------------------------
#
# Suning encodes the HVAC mode with *two different* value sets:
#
#   * ``C_MODE`` (control) — the value you send in an ``appOper`` command.
#   * ``SN_MODE`` (status) — the value the device reports back in its status.
#
# They are NOT the same encoding, so reads and writes need separate tables.
# Values below were confirmed by live-device testing (2026-06-17) plus the
# ``queryTemplate.do`` panel definition:
#
#   C_MODE (write): 1=制热 2=制冷 3=除湿 4=送风 5=送风 6=一键通(=自动)
#   SN_MODE (read): 1=一键通 2=制冷 3=制热 4=送风 5=除湿
#
# Note: this device has no dedicated AUTO mode; ``C_MODE=6`` (一键通) is the
# closest semantic match and is exposed as ``HvacMode.AUTO``. ``C_MODE=5``
# behaves the same as ``4`` (送风) on the tested device.

# Write side: C_MODE control value → HvacMode
C_FIELD_TO_HVAC: dict[str, HvacMode] = {
  "1": HvacMode.HEAT,
  "2": HvacMode.COOL,
  "3": HvacMode.DRY,
  "4": HvacMode.FAN_ONLY,
  "5": HvacMode.FAN_ONLY,
  "6": HvacMode.AUTO,
}

# Read side: SN_MODE status value → HvacMode
SN_FIELD_TO_HVAC: dict[str, HvacMode] = {
  "1": HvacMode.AUTO,
  "2": HvacMode.COOL,
  "3": HvacMode.HEAT,
  "4": HvacMode.FAN_ONLY,
  "5": HvacMode.DRY,
}

C_FIELD_TO_FAN: dict[str, FanSpeed] = {
  "0": FanSpeed.AUTO,
  "1": FanSpeed.SILENT,
  "2": FanSpeed.LOW,
  "3": FanSpeed.MEDIUM,
  "4": FanSpeed.HIGH,
  "5": FanSpeed.TURBO,
}

# HvacMode → preferred C_MODE control value (first write-table hit wins).
# QUICK shares C_MODE=6 with AUTO on the tested device (一键通 ≈ 自动).
HVAC_TO_C_FIELD: dict[HvacMode, str] = {
  HvacMode.HEAT: "1",
  HvacMode.COOL: "2",
  HvacMode.DRY: "3",
  HvacMode.FAN_ONLY: "4",
  HvacMode.AUTO: "6",
  HvacMode.QUICK: "6",
}
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
  template_id: str = "PANEL_AC",
) -> DeviceCapabilities | None:
  """Fetch the device's :class:`DeviceCapabilities`.

  Returns ``None`` on any failure (HTTP error, malformed JSON, code != 0)
  so the caller can keep going on a partial response.  Kept the legacy
  name for backward compatibility — the returned object's
  :class:`DeviceCapabilities` includes a ``raw`` payload carrying the
  unparsed template.

  The panel endpoint (``queryTemplate.do``) is queried with ``modelId``
  and ``templateId`` (confirmed from a live HAR capture).  A ``userid``
  header carrying the logged-in user's ``custno`` cookie value is sent
  so the server returns the full template instead of a login redirect.
  """

  query = f"{PANEL_QUERY_URL}?modelId={model_id}&templateId={template_id}"
  headers: dict[str, str] = {}
  custno = None
  try:
    custno = client.session.cookies.get("custno")
  except Exception:
    pass
  if custno:
    headers["userid"] = str(custno)
  try:
    response = client.session.get(query, timeout=client.timeout, headers=headers)
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
  return build_capabilities_from_template(
    device_id=device_id,
    model_id=model_id,
    category_id=category_id,
    fields=components,
    raw=data_block,
  )


def build_capabilities_from_template(
  *,
  device_id: str,
  model_id: str,
  category_id: str,
  fields: list[str],
  raw: Mapping[str, Any] | None = None,
) -> DeviceCapabilities:
  """Build a :class:`DeviceCapabilities` from a flattened field set.

  ``fields`` is the sorted list of ``C_*`` / ``SN_*`` keys returned by
  :func:`parse_panel_components`.  The boolean support flags are derived
  from membership; the HA-facing ``*_modes`` lists always include
  the standard ``off`` sentinel so the integration can render the
  toggle.
  """

  raw_dict = dict(raw) if raw else {}
  keys_block = raw_dict.get("keys") or []
  field_map: dict[str, CapabilityField] = {}
  for key_entry in keys_block:
    if not isinstance(key_entry, Mapping):
      continue
    raw_key = str(key_entry.get("key") or "")
    if not raw_key:
      continue
    field_map[raw_key] = CapabilityField(
      key=raw_key,
      name=str(key_entry.get("name") or raw_key),
      type=str(key_entry.get("type") or ""),
      raw_values=[str(v) for v in (key_entry.get("k") or [])],
      display_values=[str(v) for v in (key_entry.get("v") or [])],
      sn_property_id=key_entry.get("snPropertyId"),
      icon_urls=[str(u) for u in (key_entry.get("icon") or [])],
      raw=dict(key_entry),
    )
  # Fallback: when the panel template lacks a ``keys`` block, seed the
  # field map with placeholder CapabilityFields derived from the
  # flattened field set so callers can still ask ``"C_POWER" in
  # caps.fields``.
  for raw_key in fields:
    if raw_key in field_map:
      continue
    field_map[raw_key] = CapabilityField(
      key=raw_key,
      name=raw_key,
      type="",
    )

  has = set(fields)
  hvac_modes: list[str] = []
  # Build the hvac_modes list from the C_MODE control values the panel
  # actually advertises (its ``k`` array), mapped through the write table.
  # ``off`` is always offered (power toggle).  Unknown C_MODE values that
  # have no HvacMode mapping are simply skipped.  When the panel template
  # lacks a ``k`` array for C_MODE (e.g. no ``raw`` was supplied), fall back
  # to the full set of known modes so callers still get a usable list.
  if "C_MODE" in has:
    hvac_modes = [HvacMode.OFF.value]
    seen: set[str] = {HvacMode.OFF.value}
    mode_field = field_map.get("C_MODE")
    advertised = mode_field.raw_values if mode_field is not None else []
    if not advertised:
      advertised = list(C_FIELD_TO_HVAC.keys())
    for raw_val in advertised:
      mapped = C_FIELD_TO_HVAC.get(str(raw_val).strip())
      if mapped is not None and mapped.value not in seen:
        hvac_modes.append(mapped.value)
        seen.add(mapped.value)
  fan_modes: list[str] = []
  if "C_FANSPEED" in has:
    fan_modes = [
      FanSpeed.AUTO.value,
      FanSpeed.SILENT.value,
      FanSpeed.LOW.value,
      FanSpeed.MEDIUM.value,
      FanSpeed.HIGH.value,
      FanSpeed.TURBO.value,
    ]
  swing_modes: list[str] = []
  if "C_AIRVERTICAL" in has or "C_AIRHORIZONTAL" in has:
    swing_modes = [
      SwingMode.OFF.value,
      SwingMode.VERTICAL.value,
      SwingMode.HORIZONTAL.value,
      SwingMode.BOTH.value,
    ]
  preset_modes: list[str] = [PresetMode.NONE.value]
  if "C_ECO" in has:
    preset_modes.append(PresetMode.ECO.value)
  if "C_FRESHAIR" in has:
    preset_modes.append(PresetMode.FRESH_AIR.value)
  if "C_ELECHEATING" in has:
    preset_modes.append(PresetMode.AUX_HEAT.value)

  return DeviceCapabilities(
    device_id=device_id,
    model_id=model_id,
    category_id=category_id,
    fields=field_map,
    hvac_modes=hvac_modes,
    fan_modes=fan_modes,
    swing_modes=swing_modes,
    preset_modes=preset_modes,
    supports_vertical_swing="C_AIRVERTICAL" in has,
    supports_horizontal_swing="C_AIRHORIZONTAL" in has,
    supports_eco="C_ECO" in has,
    supports_fresh_air="C_FRESHAIR" in has,
    supports_aux_heat="C_ELECHEATING" in has,
    supports_target_temperature="C_TEMPERATURE" in has,
    raw=raw_dict,
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


def infer_hvac_mode(
  *,
  power_on: bool | None,
  mode_raw: Any,
  field_kind: str = "sn",
) -> HvacMode | None:
  """Translate raw status fields into a typed HVAC mode.

  ``power_on is False`` always wins and yields ``HvacMode.OFF``; only an
  explicitly powered-on device is mapped to a running mode.  Unknown
  mode values collapse to ``None`` so the caller can render an
  ``unavailable`` preview.

  ``field_kind`` selects the encoding table:

  * ``"sn"`` (default) — ``mode_raw`` is an ``SN_MODE`` *status* value
    (read from the device status payload); uses :data:`SN_FIELD_TO_HVAC`.
  * ``"c"`` — ``mode_raw`` is a ``C_MODE`` *control* value (the value
    you would send in an ``appOper`` command); uses
    :data:`C_FIELD_TO_HVAC`.

  The two encodings differ on this device (e.g. ``C_MODE=1`` is 制热 but
  ``SN_MODE=1`` is 一键通/自动), so callers reading device status should
  keep the default ``"sn"``.
  """

  if power_on is False:
    return HvacMode.OFF
  if power_on is not True:
    return None
  if mode_raw is None:
    return None
  table = SN_FIELD_TO_HVAC if field_kind != "c" else C_FIELD_TO_HVAC
  return table.get(str(mode_raw).strip())


def infer_fan_speed(speed_raw: Any) -> FanSpeed | None:
  """Translate a raw fan speed value into a typed :class:`FanSpeed`."""

  if speed_raw is None:
    return None
  return C_FIELD_TO_FAN.get(str(speed_raw).strip())


def infer_hvac_action(
  *,
  power_on: bool | None,
  hvac_mode: HvacMode | str | None,
  current_temp: float | None,
  target_temp: float | None,
) -> HvacAction | None:
  """Infer the device's current :class:`HvacAction` from its status fields.

  Power off → ``OFF``.  Mode is ``DRY`` / ``FAN_ONLY`` → ``DRYING`` / ``FAN``.
  Mode is ``HEAT`` or ``COOL`` → ``HEATING`` / ``COOLING`` if there is still
  work to do (current temp below / above target), else ``IDLE``.
  Mode is ``AUTO`` → behave like ``HEAT_COOL``: pick the side that has work.
  ``HEAT_COOL`` itself collapses to whichever side has work (else ``IDLE``).
  When ``power_on`` is unknown we return ``None`` so HA can render
  ``unavailable`` rather than guess.
  """

  if power_on is None:
    return None
  if power_on is False:
    return HvacAction.OFF
  if hvac_mode is None:
    return HvacAction.IDLE
  mode_value = hvac_mode.value if isinstance(hvac_mode, HvacMode) else str(hvac_mode)
  if mode_value == HvacMode.OFF.value:
    return HvacAction.OFF
  if mode_value == HvacMode.DRY.value:
    return HvacAction.DRYING
  if mode_value == HvacMode.FAN_ONLY.value:
    return HvacAction.FAN
  if current_temp is None or target_temp is None:
    return HvacAction.IDLE
  if mode_value == HvacMode.HEAT.value:
    return HvacAction.HEATING if current_temp < target_temp else HvacAction.IDLE
  if mode_value == HvacMode.COOL.value:
    return HvacAction.COOLING if current_temp > target_temp else HvacAction.IDLE
  # AUTO and QUICK (一键通) both behave like HEAT_COOL: pick the side
  # that has work to do.
  if mode_value in (HvacMode.AUTO.value, HvacMode.QUICK.value, HvacMode.HEAT_COOL.value):
    if current_temp < target_temp:
      return HvacAction.HEATING
    if current_temp > target_temp:
      return HvacAction.COOLING
    return HvacAction.IDLE
  return HvacAction.IDLE


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
  """Toggle a single preset on.  Use the dedicated setters to turn presets off."""

  if preset is PresetMode.NONE:
    raise SuningError(
      "PresetMode.NONE 不再代表'关所有预设'，请改用 set_eco / set_fresh_air / set_aux_heat"
    )
  if preset in PRESET_ON_CMD:
    return app_oper(client, device_id, model_id, PRESET_ON_CMD[preset])
  raise SuningError(f"unsupported preset mode: {preset!r}")


# ---------------------------------------------------------------------------
# Independent boolean setters (preferred for HA climate integration)
# ---------------------------------------------------------------------------


def set_vertical_swing(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
) -> dict[str, Any]:
  return app_oper(
    client,
    device_id,
    model_id,
    {"C_AIRVERTICAL": "1" if on else "0"},
  )


def set_horizontal_swing(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
) -> dict[str, Any]:
  return app_oper(
    client,
    device_id,
    model_id,
    {"C_AIRHORIZONTAL": "1" if on else "0"},
  )


def set_eco(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
) -> dict[str, Any]:
  return app_oper(client, device_id, model_id, {"C_ECO": "1" if on else "0"})


def set_fresh_air(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
) -> dict[str, Any]:
  return app_oper(
    client,
    device_id,
    model_id,
    {"C_FRESHAIR": "1" if on else "0"},
  )


def set_aux_heat(
  client: Any,
  device_id: str,
  model_id: str,
  *,
  on: bool,
  current_hvac_mode: HvacMode | str | None = None,
) -> dict[str, Any]:
  """Toggle electric auxiliary heating.

  The user-facing rule is "aux heat only when in HEAT mode".  Pass
  ``current_hvac_mode`` to enforce; if it is not ``HEAT`` (or the string
  ``"heat"``) and ``on`` is True, raise :class:`SuningError` so we never
  ship a request the device is known to reject.  When
  ``current_hvac_mode`` is ``None`` (couldn't read state) we let the
  call through and trust the device to no-op.
  """

  if on and current_hvac_mode is not None:
    normalised = (
      current_hvac_mode.value
      if isinstance(current_hvac_mode, HvacMode)
      else str(current_hvac_mode)
    )
    if normalised != HvacMode.HEAT.value:
      raise SuningError("电辅热仅在制热模式下生效")
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
  "SN_FIELD_TO_HVAC",
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
  "set_aux_heat",
  "set_eco",
  "set_fan_mode",
  "set_fresh_air",
  "set_horizontal_swing",
  "set_hvac_mode",
  "set_preset_mode",
  "set_swing_mode",
  "set_temperature",
  "set_vertical_swing",
  "turn_off",
  "turn_on",
]
