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


def test_client_does_not_auto_scan_har_files_without_explicit_path(tmp_path, monkeypatch) -> None:
  har_path = tmp_path / "signed.har"
  har_path.write_text("{}", encoding="utf-8")
  monkeypatch.chdir(tmp_path)

  client = SuningSmartHomeClient()

  assert client.signed_templates == {}




def test_client_loads_signed_templates_from_har(tmp_path) -> None:
  har_path = tmp_path / "signed.har"
  har_payload = {
    "log": {
      "entries": [
        {
          "request": {
            "method": "POST",
            "url": FAMILY_LIST_URL,
            "headers": [
              {"name": "TerminalVersion", "value": "SmartHome/6.4.5"},
              {"name": "hiro_trace_id", "value": "trace-family"},
              {"name": "snTraceId", "value": "trace-family"},
              {"name": "gsSign", "value": "family-sign"},
              {"name": "requestTime", "value": "1773960376923"},
              {"name": "terminalType", "value": "SHCSS_IOS"},
              {"name": "snTraceType", "value": "SDK"},
              {"name": "User-Agent", "value": "SmartHome/6.4.5"},
              {"name": "Content-Type", "value": "application/json"},
            ],
          },
          "response": {
            "status": 200,
            "content": {
              "text": json.dumps({"responseCode": "0", "responseMsg": "SUCCESS"}),
            },
          },
        },
        {
          "request": {
            "method": "POST",
            "url": DEVICE_LIST_URL,
            "headers": [
              {"name": "TerminalVersion", "value": "SmartHome/6.4.5"},
              {"name": "hiro_trace_id", "value": "trace-device"},
              {"name": "snTraceId", "value": "trace-device"},
              {"name": "gsSign", "value": "device-sign"},
              {"name": "requestTime", "value": "1773960378601"},
              {"name": "terminalType", "value": "SHCSS_IOS"},
              {"name": "snTraceType", "value": "SDK"},
              {"name": "User-Agent", "value": "SmartHome/6.4.5"},
              {"name": "Content-Type", "value": "application/json"},
            ],
            "postData": {
              "mimeType": "application/json",
              "text": '{\n  "familyId" : "37790"\n}',
            },
          },
          "response": {
            "status": 200,
            "content": {
              "text": json.dumps({"responseCode": "0", "responseMsg": "SUCCESS"}),
            },
          },
        },
      ]
    }
  }
  har_path.write_text(json.dumps(har_payload), encoding="utf-8")

  client = SuningSmartHomeClient(har_path=har_path)

  family_template = client._find_signed_template("POST", FAMILY_LIST_URL, "")  # noqa: SLF001
  device_template = client._find_signed_template(  # noqa: SLF001
    "POST",
    DEVICE_LIST_URL,
    '{"familyId":"37790"}',
  )

  assert family_template is not None
  assert family_template.headers["gsSign"] == "family-sign"
  assert device_template is not None
  assert device_template.headers["gsSign"] == "device-sign"
  assert client.available_device_template_family_ids() == ["37790"]


