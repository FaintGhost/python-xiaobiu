"""Air-conditioner / family / device state surface.

Functions take ``client`` by duck type and only need ``client.session``,
``client.timeout``, ``client.state``, ``client._touch_state``,
``client._resolve_ac_target`` (only for the AC control wrappers),
plus ``client._request_app_api`` and ``client._decode_app_api_response``
for the raw itapig/shcss traffic.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from .app_api import (
  decode_app_api_response,
  is_login_redirect,
)
from .exceptions import AuthenticationError, SuningError
from .models import (
  AirConditionerStatus,
  FamilyInfo,
  HAClimatePreview,
  HvacMode,
)

MEMBER_BASE_INFO_URL = "https://shcss.suning.com/shcss-web/api/member/queryMemberBaseInfo.do"
FAMILY_LIST_URL = "https://itapig.suning.com/api/trade/shcss/queryAllFamily"
DEVICE_LIST_URL = "https://itapig.suning.com/api/trade/shcss/all"
OPENSH_GET_KEY_URL = "https://opensh.suning.com/shsys-web/cc/api/v3/getKey"

SERVICE_BOOTSTRAP_URLS = {
  "shcss": MEMBER_BASE_INFO_URL,
  "itapig": "http://itapig.suning.com/api/trade/shcss/queryAllFamily",
  "opensh": OPENSH_GET_KEY_URL,
}

AIR_CONDITIONER_CATEGORY_ID = "0002"
AIR_CONDITIONER_NAME_KEYWORD = "空调"


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------


def _coalesce(*values: Any) -> Any:
  for value in values:
    if value is None:
      continue
    if isinstance(value, str) and not value.strip():
      continue
    return value
  return None


def _parse_bool_flag(value: Any) -> bool | None:
  normalized = str(value).strip().lower()
  if not normalized:
    return None
  if normalized in {"1", "true", "on", "yes"}:
    return True
  if normalized in {"0", "false", "off", "no"}:
    return False
  return None


def _parse_float_value(value: Any) -> float | None:
  if value is None:
    return None
  normalized = str(value).strip()
  if not normalized:
    return None
  try:
    return float(normalized)
  except ValueError:
    return None


def _strip_html_text(value: Any) -> str | None:
  if value is None:
    return None
  text = html.unescape(str(value))
  text = re.sub(r"<[^>]+>", "", text)
  normalized = text.strip()
  return normalized or None


def _infer_swing_mode(horizontal: bool | None, vertical: bool | None) -> str | None:
  if horizontal is True and vertical is True:
    return "both"
  if horizontal is True:
    return "horizontal"
  if vertical is True:
    return "vertical"
  if horizontal is False and vertical is False:
    return "off"
  return None


# ---------------------------------------------------------------------------
# Public AC / family / device surface
# ---------------------------------------------------------------------------


def list_families(client: Any) -> dict[str, Any]:
  response = client._request_app_api(FAMILY_LIST_URL)
  return client._decode_app_api_response(response, action="家庭列表请求")


def list_family_infos(client: Any) -> list[FamilyInfo]:
  payload = list_families(client)
  response_data = payload.get("responseData")
  if isinstance(response_data, list):
    raw_families = response_data
  elif isinstance(response_data, dict):
    raw_families = response_data.get("families") or response_data.get("familyList")
  else:
    raw_families = None
  if not isinstance(raw_families, list):
    raise SuningError("家庭列表返回格式不正确，缺少 families 数组。")

  families: list[FamilyInfo] = []
  for item in raw_families:
    if not isinstance(item, dict):
      raise SuningError("家庭列表项返回格式不正确。")
    family_id = item.get("familyId", item.get("id"))
    family_name = item.get("familyName")
    if family_id is None or family_name is None:
      raise SuningError("家庭列表项缺少 familyId 或 familyName。")
    families.append(
      FamilyInfo(
        family_id=str(family_id),
        name=str(family_name),
        raw=item,
      )
    )
  return families


def list_devices(client: Any, family_id: str | int) -> dict[str, Any]:
  request_body = json.dumps(
    {"familyId": str(family_id)},
    separators=(",", ":"),
    ensure_ascii=False,
  )
  response = client._request_app_api(DEVICE_LIST_URL, body=request_body)
  return client._decode_app_api_response(response, action="设备列表请求")


def get_device(
  client: Any,
  family_id: str | int,
  *,
  device_id: str | int | None = None,
) -> dict[str, Any]:
  payload = list_devices(client, family_id)
  devices = payload.get("responseData", {}).get("devices") or []
  if not devices:
    raise SuningError(f"familyId={family_id} 下没有设备")

  if device_id:
    for device in devices:
      if str(device.get("id")) == str(device_id):
        return device
    raise SuningError(f"familyId={family_id} 下未找到 deviceId={device_id} 的设备")

  if len(devices) == 1:
    return devices[0]

  climate_candidates = [
    device for device in devices
    if str(device.get("categoryId")) == AIR_CONDITIONER_CATEGORY_ID
    or AIR_CONDITIONER_NAME_KEYWORD in str(device.get("name", ""))
  ]
  if len(climate_candidates) == 1:
    return climate_candidates[0]

  device_hints = ", ".join(f"{item.get('id')}:{item.get('name')}" for item in devices)
  raise SuningError(
    f"familyId={family_id} 下有多个设备，请通过 --device-id 指定。可选设备: {device_hints}"
  )


def get_air_conditioner_status(
  client: Any,
  family_id: str | int,
  *,
  device_id: str | int | None = None,
) -> AirConditionerStatus:
  device = get_device(client, family_id, device_id=device_id)
  return _normalize_air_conditioner_status(device)


def list_air_conditioner_statuses(client: Any, family_id: str | int) -> list[AirConditionerStatus]:
  payload = list_devices(client, family_id)
  devices = payload.get("responseData", {}).get("devices")
  if not isinstance(devices, list):
    raise SuningError("设备列表返回格式不正确，缺少 devices 数组。")
  return [
    _normalize_air_conditioner_status(device)
    for device in devices
    if _is_air_conditioner_device(device)
  ]


def _normalize_air_conditioner_status(device: dict[str, Any]) -> AirConditionerStatus:
  raw_status = device.get("status") or {}
  online_flag = _coalesce(raw_status.get("onlineStatus"), device.get("online"))
  online = bool(_parse_bool_flag(online_flag))
  summary = _strip_html_text(device.get("p1"))
  power_on = _parse_bool_flag(_coalesce(raw_status.get("SN_POWER"), raw_status.get("C_POWER")))
  current_temperature = _parse_float_value(
    _coalesce(raw_status.get("SN_INDOORTEMP"), raw_status.get("C_INDOORTEMP"))
  )
  target_temperature = _parse_float_value(
    _coalesce(raw_status.get("SN_TEMPERATURE"), raw_status.get("C_TEMPERATURE"))
  )
  outdoor_temperature = _parse_float_value(raw_status.get("C_OUTDOORTEMP"))
  swing_horizontal = _parse_bool_flag(
    _coalesce(raw_status.get("SN_AIRHORIZONTAL"), raw_status.get("C_AIRHORIZONTAL"))
  )
  swing_vertical = _parse_bool_flag(
    _coalesce(raw_status.get("SN_AIRVERTICAL"), raw_status.get("C_AIRVERTICAL"))
  )
  eco_enabled = _parse_bool_flag(_coalesce(raw_status.get("SN_ECO"), raw_status.get("C_ECO")))
  purify_enabled = _parse_bool_flag(raw_status.get("SN_PURIFY"))
  fresh_air_enabled = _parse_bool_flag(raw_status.get("C_FRESHAIR"))
  electric_heating_enabled = _parse_bool_flag(
    _coalesce(raw_status.get("SN_ELECHEATING"), raw_status.get("C_ELECHEATING"))
  )
  mode_raw = _coalesce(raw_status.get("SN_MODE"), raw_status.get("C_MODE"))
  hvac_mode = infer_hvac_mode(power_on=power_on, mode_raw=mode_raw) if online else None

  status = AirConditionerStatus(
    device_id=str(device.get("id")),
    name=str(device.get("name") or device.get("id") or "unknown-device"),
    model=device.get("model"),
    family_id=str(device.get("fId")) if device.get("fId") is not None else None,
    group_id=str(device.get("gId")) if device.get("gId") is not None else None,
    group_name=device.get("gName"),
    category_id=str(device.get("categoryId")) if device.get("categoryId") is not None else None,
    available=online,
    online=online,
    summary=summary,
    device_record_time=device.get("time"),
    refresh_time=raw_status.get("refreshTime"),
    power_on=power_on,
    hvac_mode=hvac_mode,
    current_temperature=current_temperature,
    target_temperature=target_temperature,
    outdoor_temperature=outdoor_temperature,
    mode_raw=mode_raw,
    fan_mode_raw=_coalesce(raw_status.get("SN_FANSPEED"), raw_status.get("C_FANSPEED")),
    swing_horizontal=swing_horizontal,
    swing_vertical=swing_vertical,
    eco_enabled=eco_enabled,
    purify_enabled=purify_enabled,
    fresh_air_enabled=fresh_air_enabled,
    electric_heating_enabled=electric_heating_enabled,
    ha_climate_preview=None,
    raw_status=raw_status,
    raw_device=device,
  )
  return status.model_copy(
    update={"ha_climate_preview": _build_ha_climate_preview(status)}
  )


def infer_hvac_mode(*, power_on: bool | None, mode_raw: Any) -> HvacMode | None:
  """Translate raw status fields into a typed :class:`HvacMode`."""

  from . import ac_control

  return ac_control.infer_hvac_mode(power_on=power_on, mode_raw=mode_raw)


def _is_air_conditioner_device(device: dict[str, Any]) -> bool:
  return str(device.get("categoryId")) == AIR_CONDITIONER_CATEGORY_ID or (
    AIR_CONDITIONER_NAME_KEYWORD in str(device.get("name", ""))
  )


def _build_ha_climate_preview(status: AirConditionerStatus) -> HAClimatePreview:
  notes: list[str] = []
  if not status.available:
    notes.append("设备当前离线，Home Assistant 中应标记为 unavailable。")
  elif status.power_on is False:
    notes.append("设备已关机（power_on=false），Home Assistant 中应映射为 off。")
  elif status.power_on is None:
    notes.append("未能从原始字段中稳定解析电源状态。")

  if status.hvac_mode is None and status.power_on is True and status.mode_raw is not None:
    notes.append(
      f"原始模式值为 {status.mode_raw}，暂未在已知枚举中匹配到，Home Assistant 可保持 unavailable。"
    )

  if "C_ELECHEATING" in (status.raw_status or {}):
    notes.append(
      "C_ELECHEATING 控制路径在本次抓包中未实测，集成时建议审慎暴露电加热开关。"
    )

  supported_features_preview = [
    feature for feature in [
      "target_temperature" if status.target_temperature is not None else None,
      "current_temperature" if status.current_temperature is not None else None,
      "fan_mode" if status.fan_mode_raw is not None else None,
      "swing_mode"
      if _infer_swing_mode(status.swing_horizontal, status.swing_vertical) is not None
      else None,
      "turn_on_off" if status.power_on is not None else None,
    ]
    if feature is not None
  ]

  return HAClimatePreview(
    entity_domain="climate",
    translation_key="suning_air_conditioner",
    available=status.available,
    hvac_mode=status.hvac_mode.value if status.hvac_mode is not None else None,
    current_temperature=status.current_temperature,
    target_temperature=status.target_temperature,
    fan_mode=status.fan_mode_raw,
    swing_mode=_infer_swing_mode(status.swing_horizontal, status.swing_vertical),
    preset_mode="eco" if status.eco_enabled else None,
    supported_features_preview=supported_features_preview,
    raw_mapping={
      "power": {
        "preferred": "SN_POWER",
        "fallback": "C_POWER",
        "value": status.raw_status.get("SN_POWER") or status.raw_status.get("C_POWER"),
      },
      "mode": {
        "preferred": "SN_MODE",
        "fallback": "C_MODE",
        "value": status.mode_raw,
      },
      "target_temperature": {
        "preferred": "SN_TEMPERATURE",
        "fallback": "C_TEMPERATURE",
        "value": status.raw_status.get("SN_TEMPERATURE") or status.raw_status.get("C_TEMPERATURE"),
      },
      "current_temperature": {
        "preferred": "SN_INDOORTEMP",
        "fallback": "C_INDOORTEMP",
        "value": status.raw_status.get("SN_INDOORTEMP") or status.raw_status.get("C_INDOORTEMP"),
      },
      "fan_mode": {
        "preferred": "SN_FANSPEED",
        "fallback": "C_FANSPEED",
        "value": status.fan_mode_raw,
      },
    },
    notes=notes,
  )


# ---------------------------------------------------------------------------
# Session / service bootstrap
# ---------------------------------------------------------------------------


def bootstrap_service(client: Any, service_name: str) -> dict[str, Any]:
  if service_name not in SERVICE_BOOTSTRAP_URLS:
    raise SuningError(f"unsupported service bootstrap: {service_name}")
  response = client.session.get(
    SERVICE_BOOTSTRAP_URLS[service_name],
    timeout=client.timeout,
    allow_redirects=True,
  )
  if "/ids/login" in response.url:
    raise AuthenticationError(f"service bootstrap failed for {service_name}")
  client._touch_state()
  return {
    "service": service_name,
    "status_code": response.status_code,
    "final_url": response.url,
    "history": [item.status_code for item in response.history],
  }


def query_member_base_info(client: Any) -> dict[str, Any]:
  response = client.session.get(
    MEMBER_BASE_INFO_URL,
    timeout=client.timeout,
    allow_redirects=False,
  )
  if is_login_redirect(response):
    bootstrap_service(client, "shcss")
    response = client.session.get(
      MEMBER_BASE_INFO_URL,
      timeout=client.timeout,
      allow_redirects=False,
    )
  response.raise_for_status()
  data = response.json()
  if data.get("code") != "0":
    raise AuthenticationError(data.get("desc") or "member base info request failed")
  client._touch_state()
  return data


def keep_alive(client: Any) -> dict[str, Any]:
  member_info = query_member_base_info(client)
  return {"member": member_info}


__all__ = [
  "AIR_CONDITIONER_CATEGORY_ID",
  "AIR_CONDITIONER_NAME_KEYWORD",
  "DEVICE_LIST_URL",
  "FAMILY_LIST_URL",
  "MEMBER_BASE_INFO_URL",
  "OPENSH_GET_KEY_URL",
  "SERVICE_BOOTSTRAP_URLS",
  "bootstrap_service",
  "get_air_conditioner_status",
  "get_device",
  "infer_hvac_mode",
  "keep_alive",
  "list_air_conditioner_statuses",
  "list_devices",
  "list_families",
  "list_family_infos",
  "query_member_base_info",
]
