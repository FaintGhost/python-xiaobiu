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
  assert C_FIELD_TO_HVAC["1"] is HvacMode.COOL
  assert C_FIELD_TO_HVAC["2"] is HvacMode.HEAT
  assert C_FIELD_TO_HVAC["3"] is HvacMode.FAN_ONLY
  assert C_FIELD_TO_HVAC["4"] is HvacMode.DRY
  assert C_FIELD_TO_HVAC["5"] is HvacMode.QUICK
  assert C_FIELD_TO_HVAC["6"] is HvacMode.AUTO
  assert len(C_FIELD_TO_HVAC) == 6


def test_c_field_to_fan_maps_all_speeds() -> None:
  assert C_FIELD_TO_FAN["0"] is FanSpeed.AUTO
  assert C_FIELD_TO_FAN["1"] is FanSpeed.SILENT
  assert C_FIELD_TO_FAN["2"] is FanSpeed.LOW
  assert C_FIELD_TO_FAN["3"] is FanSpeed.MEDIUM
  assert C_FIELD_TO_FAN["4"] is FanSpeed.HIGH
  assert C_FIELD_TO_FAN["5"] is FanSpeed.TURBO
  assert len(C_FIELD_TO_FAN) == 6


def test_hvac_to_c_field_is_inverse() -> None:
  for raw, mode in C_FIELD_TO_HVAC.items():
    assert HVAC_TO_C_FIELD[mode] == raw


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
  assert "C_POWER" in template.components
  assert "C_MODE" in template.components
  called_url = client.session.get.call_args.args[0]
  assert called_url.startswith(PANEL_QUERY_URL)
  assert "deviceId=000165f9b029afa2e5d8" in called_url
  assert "modelId=0001000200150000" in called_url
  assert "categoryId=0002" in called_url


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
    (HvacMode.COOL, {"C_MODE": "1"}),
    (HvacMode.HEAT, {"C_MODE": "2"}),
    (HvacMode.FAN_ONLY, {"C_MODE": "3"}),
    (HvacMode.DRY, {"C_MODE": "4"}),
    (HvacMode.AUTO, {"C_MODE": "6"}),
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
  assert _capture_cmd(set_hvac_mode, HvacMode.QUICK) == {"C_MODE": "5"}


def test_set_aux_heat_sends_field_directly() -> None:
  pytest.importorskip("xiaobiu.ac_control", reason="high-level helpers not implemented")
  assert set_aux_heat is not None
  assert _capture_cmd(set_aux_heat, on=True) == {"C_ELECHEATING": "1"}
  assert _capture_cmd(set_aux_heat, on=False) == {"C_ELECHEATING": "0"}
