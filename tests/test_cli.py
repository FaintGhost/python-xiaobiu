from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock
from urllib.parse import unquote_plus

import pytest

from xiaobiu import SuningSmartHomeClient, parse_jsonp_or_json
from xiaobiu.client import (
  AuthenticationError,
  CaptchaRequiredError,
  CaptchaSolution,
  DEVICE_LIST_URL,
  FAMILY_LIST_URL,
  MOBILE_SMS_LOGIN_APP_CODE,
  MOBILE_SMS_LOGIN_CHANNEL,
  MOBILE_SMS_LOGIN_ORDER_CHANNEL,
  MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE,
  MOBILE_SMS_LOGIN_SCENE_ID,
  SignedRequestTemplate,
  SmsRateLimitedError,
  _air_conditioner_status_payload,
  _build_gs_sign,
  _build_parser,
  _captcha_kind_from_risk_type,
  _send_sms_with_optional_prompt,
  extract_risk_context_script_urls,
  main,
  parse_login_page_config,
  _build_captcha_from_args,
  _prompt_nonempty,
)
from xiaobiu.crypto import SuAESCipher
from xiaobiu.models import (
  AirConditionerStatus,
  CaptchaBridgeResult,
  FanSpeed,
  HvacMode,
  SwingMode,
)
from xiaobiu.exceptions import SuningError


def test_send_sms_with_iar_updates_risk_context(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  client.state.detect = "passport_detect_js_is_error"
  client.state.dfp_token = "passport_dfpToken_js_is_error"
  attempts: list[tuple[str, str, str | None]] = []

  def fake_send_sms_code(phone_number: str, *, international_code: str | None = None, captcha=None):
    attempts.append((client.state.detect, client.state.dfp_token, captcha.value if captcha else None))
    if len(attempts) == 1:
      raise CaptchaRequiredError("isIarVerifyCode", "need captcha")
    return {"status": "COMPLETE", "phone": phone_number, "internationalCode": international_code}

  monkeypatch.setattr(client, "send_sms_code", fake_send_sms_code)
  monkeypatch.setattr(
    "xiaobiu.cli._obtain_iar_captcha_result",
    lambda *_args, **_kwargs: CaptchaBridgeResult(
      token="iar-token",
      detect="browser-detect",
      dfp_token="browser-dfp",
    ),
  )

  result = _send_sms_with_optional_prompt(
    client,
    phone_number="13800000000",
    international_code="0086",
  )

  assert result["status"] == "COMPLETE"
  assert attempts == [
    ("passport_detect_js_is_error", "passport_dfpToken_js_is_error", None),
    ("browser-detect", "browser-dfp", "iar-token"),
  ]




def test_login_cli_allows_interactive_sms_code() -> None:
  parser = _build_parser()
  args = parser.parse_args(["login", "--phone", "13800000000"])
  assert args.command == "login"
  assert args.phone == "13800000000"
  assert args.sms_code is None




def test_cli_allows_shared_options_after_subcommand() -> None:
  parser = _build_parser()
  args = parser.parse_args(["families", "--har-file", "sample.har"])
  assert args.command == "families"
  assert args.har_file == "sample.har"




def test_cli_supports_device_status_command() -> None:
  parser = _build_parser()
  args = parser.parse_args(["device-status", "--family-id", "37790", "--device-id", "abc", "--raw"])
  assert args.command == "device-status"
  assert args.family_id == "37790"
  assert args.device_id == "abc"
  assert args.raw is True




def test_risk_type_to_captcha_kind_mapping() -> None:
  assert _captcha_kind_from_risk_type("isIarVerifyCode") == "iar"
  assert _captcha_kind_from_risk_type("isSlideVerifyCode") == "slide"
  assert _captcha_kind_from_risk_type("isImgVerifyCode") == "image"
  assert _captcha_kind_from_risk_type("unknown") is None




def test_login_main_reports_sms_rate_limited(monkeypatch, capsys) -> None:
  fake_client = object()

  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _args: fake_client)
  monkeypatch.setattr(
    "xiaobiu.cli._interactive_login",
    lambda *_args, **_kwargs: (_ for _ in ()).throw(
      SmsRateLimitedError("验证码发送失败，请稍后重试(00201)")
    ),
  )

  exit_code = main(["login", "--phone", "13800000000"])

  payload = json.loads(capsys.readouterr().out)
  assert exit_code == 1
  assert payload["status"] == "sms_rate_limited"
  assert payload["errorCode"] == "00201"
  assert payload["message"] == "短信发送过于频繁，请稍后再试。"
  assert payload["detail"] == "验证码发送失败，请稍后重试(00201)"




def test_cli_control_parses() -> None:
  args = _build_parser().parse_args(
    ["control", "--family-id", "37790", "--device-id", "D1", "--power", "off"],
  )
  assert args.command == "control"
  assert args.family_id == "37790"
  assert args.device_id == "D1"
  assert args.power == "off"




def test_cli_set_mode_parses() -> None:
  args = _build_parser().parse_args(
    ["set-mode", "--family-id", "37790", "--device-id", "D1", "--mode", "cool"],
  )
  assert args.command == "set-mode"
  assert args.mode == "cool"




def test_cli_set_temperature_parses() -> None:
  args = _build_parser().parse_args(
    [
      "set-temperature",
      "--family-id",
      "37790",
      "--device-id",
      "D1",
      "--temperature",
      "24.0",
    ],
  )
  assert args.command == "set-temperature"
  assert args.temperature == 24.0




def test_cli_set_fan_parses() -> None:
  args = _build_parser().parse_args(
    ["set-fan", "--family-id", "37790", "--device-id", "D1", "--speed", "low"],
  )
  assert args.command == "set-fan"
  assert args.speed == "low"




def test_cli_set_swing_parses() -> None:
  args = _build_parser().parse_args(
    ["set-swing", "--family-id", "37790", "--device-id", "D1", "--mode", "vertical"],
  )
  assert args.command == "set-swing"
  assert args.mode == "vertical"




def test_cli_set_preset_removed() -> None:
  with pytest.raises(SystemExit):
    _build_parser().parse_args(
      ["set-preset", "--family-id", "37790", "--device-id", "D1", "--preset", "eco"],
    )




def test_cli_set_eco_parses_on_off() -> None:
  args = _build_parser().parse_args(
    ["set-eco", "--family-id", "37790", "--device-id", "D1", "--on"],
  )
  assert args.command == "set-eco"
  assert args.on is True
  args = _build_parser().parse_args(
    ["set-eco", "--family-id", "37790", "--device-id", "D1", "--off"],
  )
  assert args.on is False




def test_cli_set_fresh_air_parses_on_off() -> None:
  args = _build_parser().parse_args(
    ["set-fresh-air", "--family-id", "37790", "--device-id", "D1", "--off"],
  )
  assert args.command == "set-fresh-air"
  assert args.on is False




def test_cli_set_aux_heat_parses_on_off() -> None:
  args = _build_parser().parse_args(
    ["set-aux-heat", "--family-id", "37790", "--device-id", "D1", "--on"],
  )
  assert args.command == "set-aux-heat"
  assert args.on is True




def test_cli_set_vertical_swing_parses_on_off() -> None:
  args = _build_parser().parse_args(
    ["set-vertical-swing", "--family-id", "37790", "--device-id", "D1", "--on"],
  )
  assert args.command == "set-vertical-swing"
  assert args.on is True




def test_cli_set_horizontal_swing_parses_on_off() -> None:
  args = _build_parser().parse_args(
    ["set-horizontal-swing", "--family-id", "37790", "--device-id", "D1", "--off"],
  )
  assert args.command == "set-horizontal-swing"
  assert args.on is False




def test_cli_set_fan_speed_choices_match_renamed_fan_speed() -> None:
  for speed in ("auto", "silent", "low", "medium", "high", "turbo"):
    args = _build_parser().parse_args(
      ["set-fan", "--family-id", "37790", "--device-id", "D1", "--speed", speed],
    )
    assert args.speed == speed




def test_cli_set_mode_includes_quick() -> None:
  args = _build_parser().parse_args(
    ["set-mode", "--family-id", "37790", "--device-id", "D1", "--mode", "quick"],
  )
  assert args.command == "set-mode"
  assert args.mode == "quick"




def test_cli_timers_parses() -> None:
  args = _build_parser().parse_args(
    ["timers", "--family-id", "37790", "--device-id", "D1"],
  )
  assert args.command == "timers"
  assert args.device_id == "D1"




def test_cli_panel_parses() -> None:
  args = _build_parser().parse_args(
    ["panel", "--family-id", "37790", "--device-id", "D1"],
  )
  assert args.command == "panel"
  assert args.device_id == "D1"




def test_cli_set_mode_rejects_invalid_value() -> None:
  with pytest.raises(SystemExit):
    _build_parser().parse_args(
      [
        "set-mode",
        "--family-id",
        "37790",
        "--device-id",
        "D1",
        "--mode",
        "turbo",
      ],
    )




def test_cli_control_requires_power() -> None:
  with pytest.raises(SystemExit):
    _build_parser().parse_args(
      ["control", "--family-id", "37790", "--device-id", "D1"],
    )




def test_cli_set_temperature_requires_value() -> None:
  with pytest.raises(SystemExit):
    _build_parser().parse_args(
      ["set-temperature", "--family-id", "37790", "--device-id", "D1"],
    )


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------


def test_main_send_sms_dispatches(monkeypatch, capsys) -> None:
  fake_client = MagicMock()
  fake_client.state.risk_type = "rt"
  fake_client.state.sms_ticket = "st"
  fake_client.state.login_ticket = "lt"
  fake_client.send_sms_code.return_value = {"status": "COMPLETE"}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["send-sms", "--phone", "13800000000"])
  assert rc == 0
  fake_client.send_sms_code.assert_called_once()
  out = capsys.readouterr().out
  assert "sms_sent" in out


def test_main_check_dispatches(monkeypatch, capsys) -> None:
  fake_client = MagicMock()
  fake_client.query_member_base_info.return_value = {"code": "0"}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["check"])
  assert rc == 0


def test_main_families_devices_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.list_families.return_value = {"f": 1}
  fake_client.list_devices.return_value = {"d": 1}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["families"]) == 0
  assert main(["devices", "--family-id", "1"]) == 0


def test_main_device_status_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  status = AirConditionerStatus(
    device_id="d1", name="n", available=True, online=True, power_on=True,
    hvac_mode=HvacMode.COOL, current_temperature=24.0, target_temperature=24.0,
  )
  fake_client.get_air_conditioner_status.return_value = status
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["device-status", "--family-id", "1", "--device-id", "d1", "--raw"])
  assert rc == 0


def test_main_keep_alive_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.keep_alive.return_value = {"member": {"code": "0"}}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["keep-alive"]) == 0


def test_main_control_on_off(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.turn_on.return_value = {"responseCode": "0"}
  fake_client.turn_off.return_value = {"responseCode": "0"}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["control", "--family-id", "1", "--device-id", "d1", "--power", "on"]) == 0
  assert main(["control", "--family-id", "1", "--device-id", "d1", "--power", "off"]) == 0


def test_main_set_mode_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_hvac_mode.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-mode", "--family-id", "1", "--device-id", "d1", "--mode", "cool"]) == 0
  fake_client.set_hvac_mode.assert_called_with("1", "d1", HvacMode.COOL)


def test_main_set_temperature_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_temperature.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-temperature", "--family-id", "1", "--device-id", "d1", "--temperature", "24.0"]) == 0
  fake_client.set_temperature.assert_called_with("1", "d1", 24.0)


def test_main_set_fan_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_fan_mode.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-fan", "--family-id", "1", "--device-id", "d1", "--speed", "turbo"]) == 0
  fake_client.set_fan_mode.assert_called_with("1", "d1", FanSpeed.TURBO)


def test_main_set_swing_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_swing_mode.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-swing", "--family-id", "1", "--device-id", "d1", "--mode", "both"]) == 0
  fake_client.set_swing_mode.assert_called_with("1", "d1", SwingMode.BOTH)


def test_main_set_independent_swings(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_vertical_swing.return_value = {"ok": True}
  fake_client.set_horizontal_swing.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-vertical-swing", "--family-id", "1", "--device-id", "d1", "--on"]) == 0
  assert main(["set-horizontal-swing", "--family-id", "1", "--device-id", "d1", "--off"]) == 0
  fake_client.set_vertical_swing.assert_called_with("1", "d1", on=True)
  fake_client.set_horizontal_swing.assert_called_with("1", "d1", on=False)


def test_main_set_presets(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.set_eco.return_value = {"ok": True}
  fake_client.set_fresh_air.return_value = {"ok": True}
  fake_client.set_aux_heat.return_value = {"ok": True}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["set-eco", "--family-id", "1", "--device-id", "d1", "--on"]) == 0
  assert main(["set-fresh-air", "--family-id", "1", "--device-id", "d1", "--off"]) == 0
  assert main(["set-aux-heat", "--family-id", "1", "--device-id", "d1", "--on"]) == 0


def test_main_timers_and_panel_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.list_device_timers.return_value = []
  fake_client.get_device_panel_template.return_value = None
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  assert main(["timers", "--family-id", "1", "--device-id", "d1"]) == 0
  assert main(["panel", "--family-id", "1", "--device-id", "d1"]) == 0


def test_main_captcha_required_exit_code(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.send_sms_code.side_effect = CaptchaRequiredError("isIar", "need", "st")
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["send-sms", "--phone", "13800000000"])
  assert rc == 2


def test_main_login_dispatch(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.state.risk_type = None
  fake_client.state.sms_ticket = None
  fake_client.state.login_ticket = None
  fake_client.send_sms_code.return_value = {"status": "COMPLETE"}
  fake_client.login_with_sms_code.return_value = {"ok": True}
  fake_client.query_member_base_info.return_value = {"code": "0"}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  inputs = iter(["654321"])
  monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
  rc = main(["login", "--phone", "13800000000"])
  assert rc == 0
  fake_client.login_with_sms_code.assert_called_once()


def test_main_login_with_sms_code_skips_prompt(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.login_with_sms_code.return_value = {"ok": True}
  fake_client.query_member_base_info.return_value = {"code": "0"}
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["login", "--phone", "13800000000", "--sms-code", "111111"])
  assert rc == 0


def test_main_sms_rate_limited_exit_code(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.send_sms_code.side_effect = SmsRateLimitedError("rate limited")
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["send-sms", "--phone", "13800000000"])
  assert rc == 1


def test_main_suning_error_exit_code(monkeypatch) -> None:
  fake_client = MagicMock()
  fake_client.list_families.side_effect = SuningError("boom")
  monkeypatch.setattr("xiaobiu.cli._client_from_args", lambda _a: fake_client)
  rc = main(["families"])
  assert rc == 1


def test_build_captcha_from_args_raises_when_partial() -> None:
  args = argparse.Namespace(captcha_kind="iar", captcha_value=None)
  with pytest.raises(SuningError):
    _build_captcha_from_args(args)


def test_prompt_nonempty_loops_until_valid(monkeypatch) -> None:
  inputs = iter(["", " ", "ok"])
  monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
  assert _prompt_nonempty("?") == "ok"


# ---------------------------------------------------------------------------
# Task 023 — _resolve_ac_target reads real field name
# ---------------------------------------------------------------------------


