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
from xiaobiu.exceptions import SuningError
from xiaobiu.models import CaptchaBridgeResult
from unittest.mock import MagicMock


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


# ---------------------------------------------------------------------------
# Helper-function unit tests (lifted from the refactored tests)
# ---------------------------------------------------------------------------


def test_captcha_fields_rejects_unknown_kind() -> None:
  from xiaobiu.sms_login import _captcha_fields

  with pytest.raises(SuningError, match="unsupported captcha kind"):
    _captcha_fields(CaptchaSolution(kind="unknown", value="x"))


def test_mobile_captcha_fields_rejects_unknown_kind() -> None:
  from xiaobiu.sms_login import _mobile_captcha_fields

  with pytest.raises(SuningError, match="unsupported captcha kind"):
    _mobile_captcha_fields(CaptchaSolution(kind="unknown", value="x"))


def test_captcha_fields_iar_slide_image_variants() -> None:
  from xiaobiu.sms_login import _captcha_fields

  for kind, expected_field in [
    ("iar", "iarVerifyCode"),
    ("slide", "sillerCode"),
    ("image", "imgCode"),
  ]:
    fields = _captcha_fields(CaptchaSolution(kind=kind, value="t"))
    assert fields["code"] == "t"
    assert fields[expected_field] == "t"


def test_mobile_captcha_fields_iar_has_no_uuid() -> None:
  from xiaobiu.sms_login import _mobile_captcha_fields

  fields = _mobile_captcha_fields(CaptchaSolution(kind="iar", value="t"))
  assert fields["uuid"] == ""
  assert fields["code"] == "t"


def test_uses_mobile_sms_login_only_for_mainland() -> None:
  from xiaobiu.sms_login import _uses_mobile_sms_login

  assert _uses_mobile_sms_login("0086") is True
  assert _uses_mobile_sms_login("00852") is False


def test_channel_resolves_hk_vs_mainland() -> None:
  from xiaobiu.sms_login import _channel

  assert _channel("00852") == "208000104024"
  assert _channel("0086") == "208000103001"


def test_jsonp_callback_format() -> None:
  from xiaobiu.sms_login import _jsonp_callback

  cb = _jsonp_callback("needVerifyCode")
  assert cb.startswith("needVerifyCode_")
  assert len(cb.split("_")[1]) >= 10


def test_is_login_success_matches_legacy() -> None:
  from xiaobiu.sms_login import _is_login_success

  assert _is_login_success({"success": True}) is True
  assert _is_login_success({"res_message": "SUCCESS", "res_code": "0"}) is True
  assert _is_login_success({}) is False


def test_decrypt_rdsy_response_raises_when_missing() -> None:
  from xiaobiu.sms_login import _decrypt_rdsy_response

  with pytest.raises(SuningError, match="missing _x_rdsy_resp_"):
    _decrypt_rdsy_response(MagicMock(), {})


def test_decrypt_rdsy_response_decrypts_payload() -> None:
  from xiaobiu.sms_login import _decrypt_rdsy_response

  client = MagicMock()
  client.suaes.decrypt.return_value = '{"ok": true}'
  assert _decrypt_rdsy_response(client, {"_x_rdsy_resp_": "x"}) == {"ok": True}


def test_mobile_sms_login_data_contains_required_fields() -> None:
  from xiaobiu.sms_login import _mobile_sms_login_data

  client = MagicMock()
  client.state.dfp_token = "dfp"
  data = _mobile_sms_login_data(client, "13800000000")
  assert data["dfpToken"] == "dfp"
  assert data["userName"] == "13800000000"


def test_send_sms_code_requires_phone() -> None:
  from xiaobiu.sms_login import send_sms_code

  client = MagicMock()
  client.state.phone_number = None
  with pytest.raises(SuningError, match="phone number is required"):
    send_sms_code(client)


def test_send_sms_code_raises_captcha_when_required() -> None:
  from xiaobiu.sms_login import send_sms_code

  client = MagicMock()
  client.state.phone_number = "13800000000"
  client.state.international_code = "0086"
  client.state.sms_ticket = "t"
  client.state.risk_type = "isIarVerifyCode"
  with pytest.raises(CaptchaRequiredError):
    send_sms_code(client)


def test_login_with_sms_code_requires_login_ticket() -> None:
  from xiaobiu.sms_login import login_with_sms_code

  client = MagicMock()
  client.state.phone_number = "13800000000"
  client.state.login_ticket = None
  with pytest.raises(SuningError, match="login ticket is missing"):
    login_with_sms_code(client, sms_code="123456")


def test_initialize_falls_back_to_default_on_parse_error() -> None:
  from xiaobiu.sms_login import initialize, DEFAULT_LOGIN_PAGE_CONFIG

  client = SuningSmartHomeClient()
  client.session = MagicMock()
  client.session.get.return_value.text = "<html>not a login page</html>"
  client.session.get.return_value.raise_for_status = lambda: None
  assert initialize(client) is DEFAULT_LOGIN_PAGE_CONFIG


def test_initialize_captures_script_urls() -> None:
  from xiaobiu.sms_login import initialize

  client = SuningSmartHomeClient()
  client.session = MagicMock()
  response = MagicMock()
  response.text = '<script src="https://mmds.suning.com/mmds/mmds.js?appCode=APP"></script>'
  response.raise_for_status = lambda: None
  client.session.get.return_value = response
  initialize(client)
  assert any(
    "mmds.suning.com" in url for url in client.risk_context_script_urls
  )


def test_request_iar_verify_code_ticket_raises_on_failure() -> None:
  from xiaobiu.sms_login import request_iar_verify_code_ticket

  client = MagicMock()
  client.state.dfp_token = "dfp"
  client.session.post.return_value.json.return_value = {"result": "false"}
  client.session.post.return_value.raise_for_status = lambda: None
  with pytest.raises(SuningError, match="IAR"):
    request_iar_verify_code_ticket(client, "13800000000")
