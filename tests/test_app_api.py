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


def test_signed_request_template_refreshes_trace_headers() -> None:
  template = SignedRequestTemplate(
    method="POST",
    url=FAMILY_LIST_URL,
    headers={
      "snTraceId": "old-trace",
      "hiro_trace_id": "old-trace",
      "requestTime": "1773960376923",
      "gsSign": "family-sign",
    },
  )

  headers = template.build_headers()

  assert headers["requestTime"] == "1773960376923"
  assert headers["gsSign"] == "family-sign"
  assert headers["snTraceId"] != "old-trace"
  assert headers["hiro_trace_id"] == headers["snTraceId"]




def test_build_gs_sign_matches_reverse_engineered_android_samples() -> None:
  assert _build_gs_sign("/api/trade/shcss/queryAllFamily", "1773960376923", "") == (
    "77942dbc20f6f23c0db611c070c186d0a7132c4d713f34c8e2e5b4aa34aa42f2"
  )
  assert _build_gs_sign(
    "/api/trade/shcss/all",
    "1773960378601",
    '{\n  "familyId" : "37790"\n}',
  ) == "1d6a60bf746cef243d0c3d7c595d172fc71013e707171ffd77fd7f4f87611967"


