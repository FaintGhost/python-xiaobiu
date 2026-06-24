"""Command-line interface (``xiaobiucli``) entry point.

All sub-commands thin-wrap methods on
:class:`xiaobiu.SuningSmartHomeClient`.  This module owns the argparse
parser, the interactive captcha bridge, and the formatted JSON
printing.
"""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any

from .exceptions import (
  CaptchaRequiredError,
  SmsRateLimitedError,
  SuningError,
)
from .models import AirConditionerStatus, CaptchaSolution, FanSpeed, HvacMode, SwingMode

if TYPE_CHECKING:  # pragma: no cover
  from .captcha_bridge import CaptchaBridgeResult
  from .client import SuningSmartHomeClient


def _build_parser() -> argparse.ArgumentParser:
  def add_shared_arguments(target: argparse.ArgumentParser) -> None:
    target.add_argument("--state-file", default=".suning-session.json")
    target.add_argument("--har-file")
    target.add_argument("--detect")
    target.add_argument("--dfp-token")

  parser = argparse.ArgumentParser(prog="xiaobiucli")
  add_shared_arguments(parser)
  subparsers = parser.add_subparsers(dest="command", required=True)

  send_sms = subparsers.add_parser("send-sms")
  add_shared_arguments(send_sms)
  send_sms.add_argument("--phone", required=True)
  send_sms.add_argument("--international-code", default="0086")
  send_sms.add_argument("--captcha-kind", choices=["iar", "slide", "image"])
  send_sms.add_argument("--captcha-value")

  login = subparsers.add_parser("login")
  add_shared_arguments(login)
  login.add_argument("--phone", required=True)
  login.add_argument("--sms-code")
  login.add_argument("--international-code", default="0086")
  login.add_argument("--captcha-kind", choices=["iar", "slide", "image"])
  login.add_argument("--captcha-value")

  check = subparsers.add_parser("check")
  add_shared_arguments(check)
  families = subparsers.add_parser("families")
  add_shared_arguments(families)

  devices = subparsers.add_parser("devices")
  add_shared_arguments(devices)
  devices.add_argument("--family-id", required=True)

  device_status = subparsers.add_parser("device-status")
  add_shared_arguments(device_status)
  device_status.add_argument("--family-id", required=True)
  device_status.add_argument("--device-id")
  device_status.add_argument("--raw", action="store_true")

  keep_alive = subparsers.add_parser("keep-alive")
  add_shared_arguments(keep_alive)

  control = subparsers.add_parser("control")
  add_shared_arguments(control)
  control.add_argument("--family-id", required=True)
  control.add_argument("--device-id", required=True)
  control.add_argument("--power", choices=["on", "off"], required=True)

  set_mode = subparsers.add_parser("set-mode")
  add_shared_arguments(set_mode)
  set_mode.add_argument("--family-id", required=True)
  set_mode.add_argument("--device-id", required=True)
  set_mode.add_argument(
    "--mode",
    required=True,
    choices=["off", "cool", "heat", "fan_only", "dry", "auto", "quick"],
  )

  set_temperature = subparsers.add_parser("set-temperature")
  add_shared_arguments(set_temperature)
  set_temperature.add_argument("--family-id", required=True)
  set_temperature.add_argument("--device-id", required=True)
  set_temperature.add_argument("--temperature", type=float, required=True)

  set_fan = subparsers.add_parser("set-fan")
  add_shared_arguments(set_fan)
  set_fan.add_argument("--family-id", required=True)
  set_fan.add_argument("--device-id", required=True)
  set_fan.add_argument(
    "--speed",
    required=True,
    choices=["auto", "silent", "low", "medium", "high", "turbo"],
  )

  set_swing = subparsers.add_parser("set-swing")
  add_shared_arguments(set_swing)
  set_swing.add_argument("--family-id", required=True)
  set_swing.add_argument("--device-id", required=True)
  set_swing.add_argument(
    "--mode",
    required=True,
    choices=["off", "vertical", "horizontal", "both"],
  )

  set_vertical_swing = subparsers.add_parser("set-vertical-swing")
  add_shared_arguments(set_vertical_swing)
  set_vertical_swing.add_argument("--family-id", required=True)
  set_vertical_swing.add_argument("--device-id", required=True)
  set_vertical_swing.add_argument("--on", dest="on", action="store_true", default=None)
  set_vertical_swing.add_argument("--off", dest="on", action="store_false")
  set_vertical_swing.set_defaults(on=True)

  set_horizontal_swing = subparsers.add_parser("set-horizontal-swing")
  add_shared_arguments(set_horizontal_swing)
  set_horizontal_swing.add_argument("--family-id", required=True)
  set_horizontal_swing.add_argument("--device-id", required=True)
  set_horizontal_swing.add_argument("--on", dest="on", action="store_true", default=None)
  set_horizontal_swing.add_argument("--off", dest="on", action="store_false")
  set_horizontal_swing.set_defaults(on=True)

  set_eco_cmd = subparsers.add_parser("set-eco")
  add_shared_arguments(set_eco_cmd)
  set_eco_cmd.add_argument("--family-id", required=True)
  set_eco_cmd.add_argument("--device-id", required=True)
  set_eco_cmd.add_argument("--on", dest="on", action="store_true", default=None)
  set_eco_cmd.add_argument("--off", dest="on", action="store_false")
  set_eco_cmd.set_defaults(on=True)

  set_fresh_air_cmd = subparsers.add_parser("set-fresh-air")
  add_shared_arguments(set_fresh_air_cmd)
  set_fresh_air_cmd.add_argument("--family-id", required=True)
  set_fresh_air_cmd.add_argument("--device-id", required=True)
  set_fresh_air_cmd.add_argument("--on", dest="on", action="store_true", default=None)
  set_fresh_air_cmd.add_argument("--off", dest="on", action="store_false")
  set_fresh_air_cmd.set_defaults(on=True)

  set_aux_heat_cmd = subparsers.add_parser("set-aux-heat")
  add_shared_arguments(set_aux_heat_cmd)
  set_aux_heat_cmd.add_argument("--family-id", required=True)
  set_aux_heat_cmd.add_argument("--device-id", required=True)
  set_aux_heat_cmd.add_argument("--on", dest="on", action="store_true", default=None)
  set_aux_heat_cmd.add_argument("--off", dest="on", action="store_false")
  set_aux_heat_cmd.set_defaults(on=True)

  timers_cmd = subparsers.add_parser("timers")
  add_shared_arguments(timers_cmd)
  timers_cmd.add_argument("--family-id", required=True)
  timers_cmd.add_argument("--device-id", required=True)

  panel_cmd = subparsers.add_parser("panel")
  add_shared_arguments(panel_cmd)
  panel_cmd.add_argument("--family-id", required=True)
  panel_cmd.add_argument("--device-id", required=True)

  raw_oper = subparsers.add_parser(
    "raw-oper",
    help="直接下发任意 C_*/SN_* 字段到 appOper，绕开模式映射表（用于协议实测）",
  )
  add_shared_arguments(raw_oper)
  raw_oper.add_argument("--family-id", required=True)
  raw_oper.add_argument("--device-id", required=True)
  raw_oper.add_argument(
    "--cmd",
    action="append",
    required=True,
    metavar="KEY=VALUE",
    help="要下发的字段，可多次指定，例如 --cmd C_MODE=1 --cmd C_FANSPEED=0",
  )
  return parser


def _client_from_args(args: argparse.Namespace) -> "SuningSmartHomeClient":
  # Imported here so the parser can be built without instantiating
  # requests.Session.
  from .client import SuningSmartHomeClient

  return SuningSmartHomeClient(
    state_path=args.state_file,
    har_path=args.har_file,
    detect=args.detect,
    dfp_token=args.dfp_token,
  )


def _print_payload(payload: Any) -> None:
  print(json.dumps(payload, ensure_ascii=False, indent=2))


def _air_conditioner_status_payload(
  status: AirConditionerStatus,
  *,
  include_raw: bool = False,
) -> dict[str, Any]:
  payload = status.model_dump(mode="json")
  if not include_raw:
    payload.pop("raw_status", None)
    payload.pop("raw_device", None)
  return payload


def _build_captcha_from_args(args: argparse.Namespace) -> CaptchaSolution | None:
  captcha_kind = getattr(args, "captcha_kind", None)
  captcha_value = getattr(args, "captcha_value", None)
  if captcha_kind or captcha_value:
    if not captcha_kind or not captcha_value:
      raise SuningError("captcha-kind 和 captcha-value 必须一起提供")
    return CaptchaSolution(kind=captcha_kind, value=captcha_value)
  return None


def _prompt_nonempty(prompt: str) -> str:
  while True:
    value = input(prompt).strip()
    if value:
      return value
    print("输入不能为空，请重新输入。")


def _captcha_kind_from_risk_type(risk_type: str | None) -> str | None:
  mapping = {
    "isIarVerifyCode": "iar",
    "isSlideVerifyCode": "slide",
    "isImgVerifyCode": "image",
  }
  if not risk_type:
    return None
  return mapping.get(risk_type)


def _send_sms_with_optional_prompt(
  client: "SuningSmartHomeClient",
  *,
  phone_number: str,
  international_code: str,
  captcha: CaptchaSolution | None = None,
) -> dict[str, Any]:
  active_captcha = captcha
  while True:
    try:
      return client.send_sms_code(
        phone_number,
        international_code=international_code,
        captcha=active_captcha,
      )
    except CaptchaRequiredError as error:
      captcha_kind = _captcha_kind_from_risk_type(error.risk_type)
      if not captcha_kind:
        print(
          f"发送短信前需要验证码 token，但未识别的 riskType={error.risk_type}。"
        )
        captcha_kind = _prompt_nonempty("请输入验证码类型 (iar/slide/image): ")
        if captcha_kind not in {"iar", "slide", "image"}:
          print("验证码类型只能是 iar、slide 或 image。")
          active_captcha = None
          continue
      else:
        print(
          f"发送短信前需要验证码 token，当前风控类型是 {error.risk_type}，将按 {captcha_kind} 处理。"
        )
      if captcha_kind == "iar":
        captcha_result = _obtain_iar_captcha_result(
          client,
          phone_number=phone_number,
        )
        client.update_risk_context(
          detect=captcha_result.detect,
          dfp_token=captcha_result.dfp_token,
        )
        captcha_value = captcha_result.token
      else:
        captcha_value = _prompt_nonempty("请输入验证码 token: ")
      active_captcha = CaptchaSolution(kind=captcha_kind, value=captcha_value)


def _obtain_iar_captcha_result(
  client: "SuningSmartHomeClient",
  *,
  phone_number: str,
) -> "CaptchaBridgeResult":
  # Late import — captcha_bridge is heavyweight (HTTP server templates).
  from .captcha_bridge import LocalCaptchaBridge

  iar_ticket = client.request_iar_verify_code_ticket(phone_number)
  bridge = LocalCaptchaBridge(
    ticket=iar_ticket,
    script_urls=client.risk_context_script_urls or None,
  )
  bridge.start()
  try:
    print("请在浏览器打开以下链接。进入页面后，请先点击“开始验证”，再完成苏宁拼图验证：")
    print(bridge.url)
    print("验证完成后，终端会自动继续。")
    result = bridge.wait_for_token(timeout=300.0)
    if result.detect or result.dfp_token:
      print("已收到 IAR 验证结果，并回收浏览器风控上下文，继续请求短信。")
    else:
      print("已收到 IAR 验证结果，继续请求短信。")
    return result
  finally:
    bridge.close()


def _interactive_login(
  client: "SuningSmartHomeClient",
  *,
  phone_number: str,
  international_code: str,
  sms_code: str | None,
  captcha: CaptchaSolution | None,
) -> dict[str, Any]:
  if sms_code:
    return client.login_with_sms_code(
      phone_number=phone_number,
      sms_code=sms_code,
      international_code=international_code,
    )

  sms_result = _send_sms_with_optional_prompt(
    client,
    phone_number=phone_number,
    international_code=international_code,
    captcha=captcha,
  )
  print("短信验证码已请求发送。")
  _print_payload(
    {
      "status": "sms_sent",
      "riskType": client.state.risk_type,
      "smsTicket": client.state.sms_ticket,
      "loginTicket": client.state.login_ticket,
      "response": sms_result,
    }
  )
  sms_code_input = _prompt_nonempty("请输入收到的短信验证码: ")
  return client.login_with_sms_code(
    phone_number=phone_number,
    sms_code=sms_code_input,
    international_code=international_code,
  )


def main(argv: list[str] | None = None) -> int:
  parser = _build_parser()
  args = parser.parse_args(argv)
  client = _client_from_args(args)
  try:
    if args.command == "send-sms":
      captcha = _build_captcha_from_args(args)
      payload = client.send_sms_code(
        args.phone,
        international_code=args.international_code,
        captcha=captcha,
      )
      _print_payload(
        {
          "status": "sms_sent",
          "riskType": client.state.risk_type,
          "smsTicket": client.state.sms_ticket,
          "loginTicket": client.state.login_ticket,
          "response": payload,
        }
      )
      return 0
    if args.command == "login":
      captcha = _build_captcha_from_args(args)
      payload = _interactive_login(
        client,
        phone_number=args.phone,
        sms_code=args.sms_code,
        international_code=args.international_code,
        captcha=captcha,
      )
      check_result = client.query_member_base_info()
      _print_payload(
        {
          "status": "logged_in",
          "response": payload,
          "member": check_result,
        }
      )
      return 0
    if args.command == "check":
      _print_payload(client.query_member_base_info())
      return 0
    if args.command == "families":
      _print_payload(client.list_families())
      return 0
    if args.command == "devices":
      _print_payload(client.list_devices(args.family_id))
      return 0
    if args.command == "device-status":
      _print_payload(
        _air_conditioner_status_payload(
          client.get_air_conditioner_status(
            args.family_id,
            device_id=args.device_id,
          ),
          include_raw=args.raw,
        )
      )
      return 0
    if args.command == "keep-alive":
      _print_payload(client.keep_alive())
      return 0
    if args.command == "control":
      if args.power == "off":
        payload = client.turn_off(args.family_id, args.device_id)
        command = "turn_off"
      else:
        payload = client.turn_on(args.family_id, args.device_id)
        command = "turn_on"
      _print_payload({"status": "ok", "command": command, "response": payload})
      return 0
    if args.command == "set-mode":
      payload = client.set_hvac_mode(
        args.family_id,
        args.device_id,
        HvacMode(args.mode),
      )
      _print_payload({"status": "ok", "command": "set_hvac_mode", "response": payload})
      return 0
    if args.command == "set-temperature":
      payload = client.set_temperature(
        args.family_id,
        args.device_id,
        args.temperature,
      )
      _print_payload(
        {"status": "ok", "command": "set_temperature", "response": payload},
      )
      return 0
    if args.command == "set-fan":
      payload = client.set_fan_mode(
        args.family_id,
        args.device_id,
        FanSpeed(args.speed),
      )
      _print_payload({"status": "ok", "command": "set_fan_mode", "response": payload})
      return 0
    if args.command == "set-swing":
      payload = client.set_swing_mode(
        args.family_id,
        args.device_id,
        SwingMode(args.mode),
      )
      _print_payload({"status": "ok", "command": "set_swing_mode", "response": payload})
      return 0
    if args.command == "set-vertical-swing":
      payload = client.set_vertical_swing(
        args.family_id,
        args.device_id,
        on=bool(args.on),
      )
      _print_payload(
        {"status": "ok", "command": "set_vertical_swing", "response": payload},
      )
      return 0
    if args.command == "set-horizontal-swing":
      payload = client.set_horizontal_swing(
        args.family_id,
        args.device_id,
        on=bool(args.on),
      )
      _print_payload(
        {"status": "ok", "command": "set_horizontal_swing", "response": payload},
      )
      return 0
    if args.command == "set-eco":
      payload = client.set_eco(args.family_id, args.device_id, on=bool(args.on))
      _print_payload({"status": "ok", "command": "set_eco", "response": payload})
      return 0
    if args.command == "set-fresh-air":
      payload = client.set_fresh_air(
        args.family_id,
        args.device_id,
        on=bool(args.on),
      )
      _print_payload({"status": "ok", "command": "set_fresh_air", "response": payload})
      return 0
    if args.command == "set-aux-heat":
      payload = client.set_aux_heat(
        args.family_id,
        args.device_id,
        on=bool(args.on),
      )
      _print_payload({"status": "ok", "command": "set_aux_heat", "response": payload})
      return 0
    if args.command == "timers":
      timers = client.list_device_timers(args.family_id, args.device_id)
      _print_payload([timer.model_dump(mode="json") for timer in timers])
      return 0
    if args.command == "panel":
      template = client.get_device_panel_template(args.family_id, args.device_id)
      _print_payload(
        template.model_dump(mode="json") if template is not None else None,
      )
      return 0
    if args.command == "raw-oper":
      cmd: dict[str, str] = {}
      for piece in args.cmd:
        if "=" not in piece:
          raise SuningError(f"--cmd 必须是 KEY=VALUE 形式，收到: {piece!r}")
        key, value = piece.split("=", 1)
        cmd[key.strip()] = value.strip()
      target_device, model_id = client._resolve_ac_target(
        args.family_id, args.device_id,
      )
      payload = client.app_oper(target_device, model_id, cmd)
      _print_payload(
        {
          "status": "ok",
          "command": "raw-oper",
          "device_id": target_device,
          "model_id": model_id,
          "cmd": cmd,
          "response": payload,
        },
      )
      return 0
  except CaptchaRequiredError as error:
    _print_payload(
      {
        "status": "captcha_required",
        "riskType": error.risk_type,
        "smsTicket": error.sms_ticket,
        "message": str(error),
      }
    )
    return 2
  except SmsRateLimitedError as error:
    _print_payload(
      {
        "status": "sms_rate_limited",
        "errorCode": error.error_code,
        "message": "短信发送过于频繁，请稍后再试。",
        "detail": str(error),
      }
    )
    return 1
  except SuningError as error:
    _print_payload(
      {
        "status": "error",
        "message": str(error),
      }
    )
    return 1
  return 0


__all__ = [
  "_air_conditioner_status_payload",
  "_build_captcha_from_args",
  "_build_parser",
  "_captcha_kind_from_risk_type",
  "_client_from_args",
  "_interactive_login",
  "_obtain_iar_captcha_result",
  "_print_payload",
  "_prompt_nonempty",
  "_send_sms_with_optional_prompt",
  "main",
]
