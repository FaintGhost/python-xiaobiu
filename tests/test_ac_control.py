"""Tests for xiaobiu.ac_control (Tasks 002, 003, 005, 006)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from xiaobiu import (
  FanSpeed,
  HvacMode,
  PresetMode,
  SwingMode,
)
from xiaobiu.ac_control import (
  APP_OPER_URL,
  C_FIELD_TO_FAN,
  C_FIELD_TO_HVAC,
  FAN_TO_C_FIELD,
  HVAC_TO_C_FIELD,
  PANEL_QUERY_URL,
  PRESET_OFF_CMD,
  PRESET_ON_CMD,
  QUERY_TIMER_URL,
  SN_FIELD_TO_HVAC,
  SWING_TO_CMD,
)
from xiaobiu.client import SuningError

# Lazy imports of modules under test so a missing symbol fails only the
# relevant tests (pytest still surfaces collection errors, but this way
# each test advertises the symbol it depends on).
try:  # pragma: no cover - import shim for TDD
  from xiaobiu.ac_control import app_oper  # type: ignore
except ImportError:  # pragma: no cover
  app_oper = None  # type: ignore[assignment]
try:  # pragma: no cover
  from xiaobiu.ac_control import get_device_panel_template  # type: ignore
except ImportError:  # pragma: no cover
  get_device_panel_template = None  # type: ignore[assignment]
try:  # pragma: no cover
  from xiaobiu.ac_control import list_device_timers  # type: ignore
except ImportError:  # pragma: no cover
  list_device_timers = None  # type: ignore[assignment]
try:  # pragma: no cover
  from xiaobiu.ac_control import parse_panel_components  # type: ignore
except ImportError:  # pragma: no cover
  parse_panel_components = None  # type: ignore[assignment]
try:  # pragma: no cover
  from xiaobiu.ac_control import turn_on  # type: ignore
  from xiaobiu.ac_control import turn_off  # type: ignore
  from xiaobiu.ac_control import set_hvac_mode  # type: ignore
  from xiaobiu.ac_control import set_temperature  # type: ignore
  from xiaobiu.ac_control import set_fan_mode  # type: ignore
  from xiaobiu.ac_control import set_swing_mode  # type: ignore
  from xiaobiu.ac_control import set_preset_mode  # type: ignore
  from xiaobiu.ac_control import set_eco  # type: ignore
  from xiaobiu.ac_control import set_fresh_air  # type: ignore
  from xiaobiu.ac_control import set_aux_heat  # type: ignore
  from xiaobiu.ac_control import set_vertical_swing  # type: ignore
  from xiaobiu.ac_control import set_horizontal_swing  # type: ignore
except ImportError:  # pragma: no cover
  turn_on = turn_off = set_hvac_mode = set_temperature = None  # type: ignore[assignment]
  set_fan_mode = set_swing_mode = set_preset_mode = None  # type: ignore[assignment]
  set_eco = set_fresh_air = set_aux_heat = None  # type: ignore[assignment]
  set_vertical_swing = set_horizontal_swing = None  # type: ignore[assignment]


def test_c_field_to_hvac_maps_all_modes() -> None:
  # C_MODE control values, confirmed by live-device testing (2026-06-17):
  #   1=制热 2=制冷 3=除湿 4=送风 5=送风 6=一键通(=自动)
  assert C_FIELD_TO_HVAC["1"] is HvacMode.HEAT
  assert C_FIELD_TO_HVAC["2"] is HvacMode.COOL
  assert C_FIELD_TO_HVAC["3"] is HvacMode.DRY
  assert C_FIELD_TO_HVAC["4"] is HvacMode.FAN_ONLY
  assert C_FIELD_TO_HVAC["5"] is HvacMode.FAN_ONLY
  assert C_FIELD_TO_HVAC["6"] is HvacMode.AUTO
  assert len(C_FIELD_TO_HVAC) == 6


def test_sn_field_to_hvac_maps_status_values() -> None:
  # SN_MODE status values, from queryTemplate.do snV array:
  #   1=一键通(自动) 2=制冷 3=制热 4=送风 5=除湿
  assert SN_FIELD_TO_HVAC["1"] is HvacMode.AUTO
  assert SN_FIELD_TO_HVAC["2"] is HvacMode.COOL
  assert SN_FIELD_TO_HVAC["3"] is HvacMode.HEAT
  assert SN_FIELD_TO_HVAC["4"] is HvacMode.FAN_ONLY
  assert SN_FIELD_TO_HVAC["5"] is HvacMode.DRY
  assert len(SN_FIELD_TO_HVAC) == 5


def test_c_field_to_fan_maps_all_speeds() -> None:
  assert C_FIELD_TO_FAN["0"] is FanSpeed.AUTO
  assert C_FIELD_TO_FAN["1"] is FanSpeed.SILENT
  assert C_FIELD_TO_FAN["2"] is FanSpeed.LOW
  assert C_FIELD_TO_FAN["3"] is FanSpeed.MEDIUM
  assert C_FIELD_TO_FAN["4"] is FanSpeed.HIGH
  assert C_FIELD_TO_FAN["5"] is FanSpeed.TURBO
  assert len(C_FIELD_TO_FAN) == 6


def test_hvac_to_c_field_maps_preferred_control_value() -> None:
  # HVAC_TO_C_FIELD is no longer a strict inverse of C_FIELD_TO_HVAC because
  # several HvacMode values share a C_MODE code (FAN_ONLY←4,5; AUTO/QUICK←6).
  # It must map each supported mode to its preferred control value.
  assert HVAC_TO_C_FIELD[HvacMode.HEAT] == "1"
  assert HVAC_TO_C_FIELD[HvacMode.COOL] == "2"
  assert HVAC_TO_C_FIELD[HvacMode.DRY] == "3"
  assert HVAC_TO_C_FIELD[HvacMode.FAN_ONLY] == "4"
  assert HVAC_TO_C_FIELD[HvacMode.AUTO] == "6"
  assert HVAC_TO_C_FIELD[HvacMode.QUICK] == "6"


def test_fan_to_c_field_is_inverse() -> None:
  for raw, speed in C_FIELD_TO_FAN.items():
    assert FAN_TO_C_FIELD[speed] == raw


def test_swing_to_cmd_covers_all_modes() -> None:
  assert SWING_TO_CMD[SwingMode.OFF] == {
    "C_AIRVERTICAL": "0",
    "C_AIRHORIZONTAL": "0",
  }
  assert SWING_TO_CMD[SwingMode.VERTICAL] == {
    "C_AIRVERTICAL": "1",
    "C_AIRHORIZONTAL": "0",
  }
  assert SWING_TO_CMD[SwingMode.HORIZONTAL] == {
    "C_AIRVERTICAL": "0",
    "C_AIRHORIZONTAL": "1",
  }
  assert SWING_TO_CMD[SwingMode.BOTH] == {
    "C_AIRVERTICAL": "1",
    "C_AIRHORIZONTAL": "1",
  }


def test_preset_on_cmd_eco_and_fresh_air() -> None:
  assert PRESET_ON_CMD[PresetMode.ECO] == {"C_ECO": "1"}
  assert PRESET_ON_CMD[PresetMode.FRESH_AIR] == {"C_FRESHAIR": "1"}


def test_preset_off_cmd_eco_and_fresh_air() -> None:
  assert PRESET_OFF_CMD[PresetMode.ECO] == {"C_ECO": "0"}
  assert PRESET_OFF_CMD[PresetMode.FRESH_AIR] == {"C_FRESHAIR": "0"}


# ---------------------------------------------------------------------------
# Task 003 — app_oper
# ---------------------------------------------------------------------------


def _ok_app_oper_response() -> dict:
  return {
    "responseCode": "0",
    "responseData": {"code": "0", "time": "2026-06-01 23:23:18"},
  }


def _make_client_mock(*, response: dict | Exception) -> MagicMock:
  client = MagicMock()
  if isinstance(response, Exception):
    client._request_app_api.side_effect = response
  else:
    response_obj = MagicMock()
    response_obj.json.return_value = response
    client._request_app_api.return_value = response_obj
  return client


def test_app_oper_single_field_calls_request_app_api() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="app_oper not implemented")
  assert app_oper is not None
  client = _make_client_mock(response=_ok_app_oper_response())
  payload = app_oper(client, "000165f9b029afa2e5d8", "0001000200150000", {"C_POWER": "1"})
  assert payload["responseCode"] == "0"
  assert client._request_app_api.call_count == 1
  args, kwargs = client._request_app_api.call_args
  assert args[0] == APP_OPER_URL
  body = kwargs["body"]
  parsed = json.loads(body)
  assert parsed["deviceId"] == "000165f9b029afa2e5d8"
  assert parsed["modelId"] == "0001000200150000"
  cmd = json.loads(parsed["cmd"])
  assert cmd == {"C_POWER": "1"}
  # Compact JSON has no spaces.
  assert " " not in parsed["cmd"]


def test_app_oper_multiple_fields_serialised_compactly() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="app_oper not implemented")
  assert app_oper is not None
  client = _make_client_mock(response=_ok_app_oper_response())
  app_oper(
    client,
    "dev",
    "mod",
    {"C_TEMPERATURE": "24.0", "C_FANSPEED": "2"},
  )
  body = client._request_app_api.call_args.kwargs["body"]
  cmd = json.loads(json.loads(body)["cmd"])
  assert cmd == {"C_TEMPERATURE": "24.0", "C_FANSPEED": "2"}


def test_app_oper_stringifies_values() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="app_oper not implemented")
  assert app_oper is not None
  client = _make_client_mock(response=_ok_app_oper_response())
  app_oper(client, "dev", "mod", {"C_TEMPERATURE": 24.0, "C_FANSPEED": 2})
  body = client._request_app_api.call_args.kwargs["body"]
  cmd = json.loads(json.loads(body)["cmd"])
  assert cmd["C_TEMPERATURE"] == "24.0"
  assert cmd["C_FANSPEED"] == "2"
  assert all(isinstance(v, str) for v in cmd.values())


def test_app_oper_raises_on_business_error() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="app_oper not implemented")
  assert app_oper is not None
  client = _make_client_mock(
    response={"responseCode": "1", "responseMsg": "device offline"},
  )
  with pytest.raises(SuningError, match="device offline"):
    app_oper(client, "dev", "mod", {"C_POWER": "1"})


def test_app_oper_raises_on_invalid_json() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="app_oper not implemented")
  assert app_oper is not None
  client = MagicMock()
  response_obj = MagicMock()
  response_obj.json.side_effect = ValueError("nope")
  client._request_app_api.return_value = response_obj
  with pytest.raises(SuningError):
    app_oper(client, "dev", "mod", {"C_POWER": "1"})


# ---------------------------------------------------------------------------
# Task 005 — panel template
# ---------------------------------------------------------------------------


PANEL_CONTAINERS = [
  {
    "containerId": "TOP",
    "component": (
      "[{\"COM_STATE\":\"C_MODE,C_FANSPEED,C_AIRVERTICAL,C_AIRHORIZONTAL,"
      "C_ECO,C_FRESHAIR,C_ELECHEATING,SN_CLOUD_TIMER\"},"
      "{\"COM_POWER\":\"C_POWER\"}]"
    ),
  },
]


def test_parse_panel_components_extracts_field_set() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="parse_panel_components not implemented")
  assert parse_panel_components is not None
  fields = parse_panel_components(PANEL_CONTAINERS)
  assert fields == sorted(
    {
      "C_MODE",
      "C_FANSPEED",
      "C_AIRVERTICAL",
      "C_AIRHORIZONTAL",
      "C_ECO",
      "C_FRESHAIR",
      "C_ELECHEATING",
      "SN_CLOUD_TIMER",
      "C_POWER",
    }
  )


def test_parse_panel_components_returns_none_on_bad_json() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="parse_panel_components not implemented")
  assert parse_panel_components is not None
  assert parse_panel_components([{"component": "{not json"}]) is None


def test_parse_panel_components_returns_none_on_non_list() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="parse_panel_components not implemented")
  assert parse_panel_components is not None
  assert parse_panel_components([{"component": "{}"}]) is None


def test_get_device_panel_template_hits_url_and_parses() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  assert get_device_panel_template is not None
  client = MagicMock()
  response = MagicMock()
  response.json.return_value = {
    "code": "0",
    "data": {"templateId": "PANEL_AC", "containers": PANEL_CONTAINERS},
  }
  response.raise_for_status.return_value = None
  client.session.get.return_value = response
  template = get_device_panel_template(
    client,
    device_id="000165f9b029afa2e5d8",
    model_id="0001000200150000",
  )
  assert template is not None
  assert template.device_id == "000165f9b029afa2e5d8"
  assert template.model_id == "0001000200150000"
  assert "C_POWER" in template.fields
  assert "C_MODE" in template.fields
  assert "cool" in template.hvac_modes
  called_url = client.session.get.call_args.args[0]
  assert called_url.startswith(PANEL_QUERY_URL)
  assert "modelId=0001000200150000" in called_url
  assert "templateId=PANEL_AC" in called_url
  assert "deviceId=" not in called_url
  assert "categoryId=" not in called_url


def test_get_device_panel_template_returns_none_on_error_code() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  assert get_device_panel_template is not None
  client = MagicMock()
  response = MagicMock()
  response.json.return_value = {"code": "1", "desc": "boom"}
  response.raise_for_status.return_value = None
  client.session.get.return_value = response
  assert get_device_panel_template(client, "d", "m") is None


def test_get_device_panel_template_returns_none_on_exception() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  assert get_device_panel_template is not None
  client = MagicMock()
  client.session.get.side_effect = RuntimeError("network")
  assert get_device_panel_template(client, "d", "m") is None


def test_get_device_panel_template_sends_userid_header_from_custno_cookie() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  client = MagicMock()
  client.session.cookies.get.return_value = "7406242293"
  response = MagicMock()
  response.json.return_value = {"code": "0", "data": {"containers": []}}
  response.raise_for_status.return_value = None
  client.session.get.return_value = response
  get_device_panel_template(client, "d", "m")
  call_kwargs = client.session.get.call_args.kwargs
  assert call_kwargs["headers"]["userid"] == "7406242293"


def test_get_device_panel_template_omits_userid_when_no_custno_cookie() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  client = MagicMock()
  client.session.cookies.get.return_value = None
  response = MagicMock()
  response.json.return_value = {"code": "0", "data": {"containers": []}}
  response.raise_for_status.return_value = None
  client.session.get.return_value = response
  get_device_panel_template(client, "d", "m")
  call_kwargs = client.session.get.call_args.kwargs
  assert "headers" not in call_kwargs or "userid" not in call_kwargs.get("headers", {})


def test_get_device_panel_template_accepts_custom_template_id() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="get_device_panel_template not implemented")
  client = MagicMock()
  client.session.cookies.get.return_value = None
  response = MagicMock()
  response.json.return_value = {"code": "0", "data": {"containers": []}}
  response.raise_for_status.return_value = None
  client.session.get.return_value = response
  get_device_panel_template(client, "d", "m", template_id="PANEL_CUSTOM")
  called_url = client.session.get.call_args.args[0]
  assert "templateId=PANEL_CUSTOM" in called_url


# ---------------------------------------------------------------------------
# Task 006 — timers
# ---------------------------------------------------------------------------


TIMER_RESPONSE = {
  "responseCode": "0",
  "responseData": {
    "data": [
      {"timer": "F,00,30,0", "timerName": "关闭时间", "state": "-1", "timerCmd": {"C_POWER": "0"}},
      {"timer": "F,11,40,0", "timerName": "开启时间", "state": "0", "timerCmd": {"C_POWER": "1"}},
    ]
  },
}


def test_list_device_timers_parses_state_and_fields() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="list_device_timers not implemented")
  assert list_device_timers is not None
  client = _make_client_mock(response=TIMER_RESPONSE)
  timers = list_device_timers(client, "000165f9b029afa2e5d8")
  assert len(timers) == 2
  assert timers[0].name == "关闭时间"
  assert timers[0].schedule == "F,00,30,0"
  assert timers[0].enabled is False
  assert timers[0].command == {"C_POWER": "0"}
  assert timers[1].name == "开启时间"
  assert timers[1].enabled is True
  # body carries the device id
  body = client._request_app_api.call_args.kwargs["body"]
  assert json.loads(body)["deviceId"] == "000165f9b029afa2e5d8"
  assert client._request_app_api.call_args.args[0] == QUERY_TIMER_URL


def test_list_device_timers_raises_on_business_error() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="list_device_timers not implemented")
  assert list_device_timers is not None
  client = _make_client_mock(
    response={"responseCode": "1", "responseMsg": "forbidden"},
  )
  with pytest.raises(SuningError, match="forbidden"):
    list_device_timers(client, "dev")


def test_list_device_timers_raises_on_bad_payload() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="list_device_timers not implemented")
  assert list_device_timers is not None
  client = _make_client_mock(
    response={"responseCode": "0", "responseData": {"data": "nope"}},
  )
  with pytest.raises(SuningError, match="定时列表格式不正确"):
    list_device_timers(client, "dev")


# ---------------------------------------------------------------------------
# Task 004 — high-level helpers
# ---------------------------------------------------------------------------


def _capture_cmd(target, *args, **kwargs) -> dict:
  client = MagicMock()
  response = MagicMock()
  response.json.return_value = {
    "responseCode": "0",
    "responseData": {"code": "0"},
  }
  client._request_app_api.return_value = response
  target(client, "dev", "mod", *args, **kwargs)
  body = client._request_app_api.call_args.kwargs["body"]
  outer = json.loads(body)
  return json.loads(outer["cmd"])


def test_turn_on_sends_c_power_on() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert turn_on is not None
  assert _capture_cmd(turn_on) == {"C_POWER": "1"}


def test_turn_off_sends_c_power_off() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert turn_off is not None
  assert _capture_cmd(turn_off) == {"C_POWER": "0"}


@pytest.mark.parametrize(
  "mode,expected",
  [
    (HvacMode.HEAT, {"C_MODE": "1"}),
    (HvacMode.COOL, {"C_MODE": "2"}),
    (HvacMode.DRY, {"C_MODE": "3"}),
    (HvacMode.FAN_ONLY, {"C_MODE": "4"}),
    (HvacMode.AUTO, {"C_MODE": "6"}),
    (HvacMode.QUICK, {"C_MODE": "6"}),
  ],
)
def test_set_hvac_mode_sends_c_mode(mode, expected) -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_hvac_mode is not None
  assert _capture_cmd(set_hvac_mode, mode) == expected


def test_set_hvac_mode_off_turns_power_off() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_hvac_mode is not None
  assert _capture_cmd(set_hvac_mode, HvacMode.OFF) == {"C_POWER": "0"}


def test_set_temperature_sends_value() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_temperature is not None
  assert _capture_cmd(set_temperature, 24.0) == {"C_TEMPERATURE": "24.0"}


def test_set_temperature_rejects_non_numeric() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_temperature is not None
  with pytest.raises(ValueError):
    set_temperature(MagicMock(), "dev", "mod", "abc")


@pytest.mark.parametrize("bad", [5.0, 10.0, 40.0, 50.0])
def test_set_temperature_rejects_out_of_range(bad) -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_temperature is not None
  with pytest.raises(ValueError):
    set_temperature(MagicMock(), "dev", "mod", bad)


@pytest.mark.parametrize("good", [16.0, 24.0, 32.0])
def test_set_temperature_accepts_boundaries(good) -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_temperature is not None
  assert _capture_cmd(set_temperature, good) == {"C_TEMPERATURE": str(good)}


@pytest.mark.parametrize(
  "speed,expected",
  [
    (FanSpeed.AUTO, {"C_FANSPEED": "0"}),
    (FanSpeed.SILENT, {"C_FANSPEED": "1"}),
    (FanSpeed.LOW, {"C_FANSPEED": "2"}),
    (FanSpeed.MEDIUM, {"C_FANSPEED": "3"}),
    (FanSpeed.HIGH, {"C_FANSPEED": "4"}),
    (FanSpeed.TURBO, {"C_FANSPEED": "5"}),
  ],
)
def test_set_fan_mode_sends_c_fanspeed(speed, expected) -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_fan_mode is not None
  assert _capture_cmd(set_fan_mode, speed) == expected


@pytest.mark.parametrize(
  "swing,expected",
  [
    (SwingMode.OFF, {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "0"}),
    (SwingMode.VERTICAL, {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "0"}),
    (SwingMode.HORIZONTAL, {"C_AIRVERTICAL": "0", "C_AIRHORIZONTAL": "1"}),
    (SwingMode.BOTH, {"C_AIRVERTICAL": "1", "C_AIRHORIZONTAL": "1"}),
  ],
)
def test_set_swing_mode_sends_swing_cmd(swing, expected) -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_swing_mode is not None
  assert _capture_cmd(set_swing_mode, swing) == expected


def test_set_preset_mode_eco_sends_c_eco_on() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_preset_mode is not None
  assert _capture_cmd(set_preset_mode, PresetMode.ECO) == {"C_ECO": "1"}


def test_set_preset_mode_fresh_air_sends_c_freshair_on() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_preset_mode is not None
  assert _capture_cmd(set_preset_mode, PresetMode.FRESH_AIR) == {"C_FRESHAIR": "1"}


def test_set_preset_mode_none_now_raises() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_preset_mode is not None
  with pytest.raises(SuningError, match="NONE"):
    set_preset_mode(MagicMock(), "dev", "mod", PresetMode.NONE)


def test_set_eco_sends_field() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_eco not implemented")
  assert set_eco is not None
  assert _capture_cmd(set_eco, on=True) == {"C_ECO": "1"}
  assert _capture_cmd(set_eco, on=False) == {"C_ECO": "0"}


def test_set_fresh_air_sends_field() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_fresh_air not implemented")
  assert set_fresh_air is not None
  assert _capture_cmd(set_fresh_air, on=True) == {"C_FRESHAIR": "1"}
  assert _capture_cmd(set_fresh_air, on=False) == {"C_FRESHAIR": "0"}


def test_set_aux_heat_off_always_passes_through() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_aux_heat not implemented")
  assert set_aux_heat is not None
  assert _capture_cmd(set_aux_heat, on=False, current_hvac_mode=HvacMode.COOL) == {
    "C_ELECHEATING": "0"
  }
  assert _capture_cmd(set_aux_heat, on=False, current_hvac_mode=None) == {
    "C_ELECHEATING": "0"
  }


def test_set_aux_heat_on_requires_heat_mode() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_aux_heat not implemented")
  assert set_aux_heat is not None
  assert _capture_cmd(set_aux_heat, on=True, current_hvac_mode=HvacMode.HEAT) == {
    "C_ELECHEATING": "1"
  }
  for mode in (HvacMode.COOL, HvacMode.DRY, HvacMode.FAN_ONLY, HvacMode.AUTO, HvacMode.OFF):
    with pytest.raises(SuningError, match="制热"):
      set_aux_heat(MagicMock(), "dev", "mod", on=True, current_hvac_mode=mode)


def test_set_aux_heat_on_with_unknown_mode_is_allowed() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_aux_heat not implemented")
  assert set_aux_heat is not None
  # Status read failure (None) should not block — trust the device.
  assert _capture_cmd(set_aux_heat, on=True, current_hvac_mode=None) == {
    "C_ELECHEATING": "1"
  }


def test_set_vertical_swing_sends_field() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_vertical_swing not implemented")
  assert set_vertical_swing is not None
  assert _capture_cmd(set_vertical_swing, on=True) == {"C_AIRVERTICAL": "1"}
  assert _capture_cmd(set_vertical_swing, on=False) == {"C_AIRVERTICAL": "0"}


def test_set_horizontal_swing_sends_field() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_horizontal_swing not implemented")
  assert set_horizontal_swing is not None
  assert _capture_cmd(set_horizontal_swing, on=True) == {"C_AIRHORIZONTAL": "1"}
  assert _capture_cmd(set_horizontal_swing, on=False) == {"C_AIRHORIZONTAL": "0"}


def test_set_hvac_mode_quick_sends_c_mode_5() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="set_hvac_mode not implemented")
  assert set_hvac_mode is not None
  assert _capture_cmd(set_hvac_mode, HvacMode.QUICK) == {"C_MODE": "6"}


def test_set_aux_heat_sends_field_directly() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_aux_heat is not None
  assert _capture_cmd(set_aux_heat, on=True) == {"C_ELECHEATING": "1"}
  assert _capture_cmd(set_aux_heat, on=False) == {"C_ELECHEATING": "0"}


# ---------------------------------------------------------------------------
# infer_hvac_action
# ---------------------------------------------------------------------------


def test_infer_hvac_action_off_when_power_off() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=False, hvac_mode=HvacMode.HEAT, current_temp=10.0, target_temp=20.0,
    )
    == "off"
  )


def test_infer_hvac_action_none_when_power_unknown() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=None, hvac_mode=HvacMode.HEAT, current_temp=10.0, target_temp=20.0,
    )
    is None
  )


def test_infer_hvac_action_heating_when_below_target() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.HEAT,
      current_temp=18.0, target_temp=22.0,
    )
    == "heating"
  )


def test_infer_hvac_action_cooling_when_above_target() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.COOL,
      current_temp=28.0, target_temp=24.0,
    )
    == "cooling"
  )


def test_infer_hvac_action_idle_when_at_target() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.HEAT,
      current_temp=22.0, target_temp=22.0,
    )
    == "idle"
  )


def test_infer_hvac_action_dry_and_fan() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.DRY, current_temp=24.0, target_temp=24.0,
    )
    == "drying"
  )
  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.FAN_ONLY, current_temp=24.0, target_temp=24.0,
    )
    == "fan"
  )


def test_infer_hvac_action_auto_picks_heating_or_cooling() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.AUTO,
      current_temp=18.0, target_temp=22.0,
    )
    == "heating"
  )
  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.AUTO,
      current_temp=28.0, target_temp=22.0,
    )
    == "cooling"
  )
  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.AUTO,
      current_temp=22.0, target_temp=22.0,
    )
    == "idle"
  )


def test_infer_hvac_action_quick_treated_like_heat() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.QUICK,
      current_temp=18.0, target_temp=22.0,
    )
    == "heating"
  )


def test_infer_hvac_action_idle_when_temps_missing() -> None:
  from xiaobiu.ac_control import infer_hvac_action

  assert (
    infer_hvac_action(
      power_on=True, hvac_mode=HvacMode.HEAT, current_temp=None, target_temp=22.0,
    )
    == "idle"
  )


# ---------------------------------------------------------------------------
# build_capabilities_from_template
# ---------------------------------------------------------------------------


def test_build_capabilities_emits_modes_for_supported_fields() -> None:
  from xiaobiu.ac_control import build_capabilities_from_template

  caps = build_capabilities_from_template(
    device_id="d",
    model_id="m",
    category_id="0002",
    fields=["C_MODE", "C_FANSPEED", "C_AIRVERTICAL", "C_AIRHORIZONTAL", "C_ECO"],
  )
  assert "cool" in caps.hvac_modes
  assert "heat" in caps.hvac_modes
  assert "auto" in caps.fan_modes
  assert "turbo" in caps.fan_modes
  assert "off" in caps.swing_modes
  assert "both" in caps.swing_modes
  assert "eco" in caps.preset_modes
  assert caps.supports_vertical_swing is True
  assert caps.supports_horizontal_swing is True
  assert caps.supports_eco is True
  assert caps.supports_fresh_air is False


def test_build_capabilities_marks_no_fields_when_template_empty() -> None:
  from xiaobiu.ac_control import build_capabilities_from_template

  caps = build_capabilities_from_template(
    device_id="d", model_id="m", category_id="0002", fields=[],
  )
  assert caps.hvac_modes == []
  assert caps.fan_modes == []
  assert caps.swing_modes == []
  assert caps.preset_modes == ["none"]
  assert caps.supports_vertical_swing is False


def test_build_capabilities_includes_aux_heat_when_field_present() -> None:
  from xiaobiu.ac_control import build_capabilities_from_template

  caps = build_capabilities_from_template(
    device_id="d", model_id="m", category_id="0002",
    fields=["C_MODE", "C_ELECHEATING"],
  )
  assert "aux_heat" in caps.preset_modes
  assert caps.supports_aux_heat is True


def test_build_capabilities_auto_appears_in_hvac_modes() -> None:
  from xiaobiu.ac_control import build_capabilities_from_template

  caps = build_capabilities_from_template(
    device_id="d", model_id="m", category_id="0002", fields=["C_MODE"],
  )
  # 一键通 is exposed as AUTO on the tested device (C_MODE=6).
  assert "auto" in caps.hvac_modes

