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


def test_captcha_field_mapping() -> None:
  client = SuningSmartHomeClient()
  fields = client._captcha_fields(CaptchaSolution(kind="iar", value="token"))  # noqa: SLF001
  assert fields["uuid"] == "iarVerifyCode"
  assert fields["code"] == "token"




def test_mobile_captcha_field_mapping() -> None:
  client = SuningSmartHomeClient()
  fields = client._mobile_captcha_fields(CaptchaSolution(kind="iar", value="token"))  # noqa: SLF001
  assert fields["uuid"] == ""
  assert fields["code"] == "token"
  assert "iarVerifyCode" not in fields


