from __future__ import annotations

import json
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
  main as client_main,
  parse_login_page_config,
)
from xiaobiu.crypto import SuAESCipher
from xiaobiu.models import CaptchaBridgeResult


def test_state_file_roundtrip(tmp_path) -> None:
  state_path = tmp_path / "session.json"
  client = SuningSmartHomeClient(state_path=state_path)
  client.state.phone_number = "13800000000"
  client.state.sms_ticket = "SMS_TICKET"
  client.session.cookies.set("authId", "cookie-value", domain=".suning.com", path="/")
  client.save_state()

  reloaded = SuningSmartHomeClient(state_path=state_path)
  assert reloaded.state.phone_number == "13800000000"
  assert reloaded.state.sms_ticket == "SMS_TICKET"
  assert reloaded.session.cookies.get("authId", domain=".suning.com", path="/") == "cookie-value"


