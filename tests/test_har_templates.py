from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Helper-function unit tests
# ---------------------------------------------------------------------------


def test_normalize_url_strips_query_and_fragment() -> None:
  from xiaobiu.har_templates import normalize_url

  assert normalize_url("https://example.com:8080/path?x=1#y") == "https://example.com:8080/path"


def test_canonicalize_request_body_returns_empty_for_empty() -> None:
  from xiaobiu.har_templates import canonicalize_request_body

  assert canonicalize_request_body(None) == ""
  assert canonicalize_request_body("") == ""
  assert canonicalize_request_body("  ") == ""


def test_canonicalize_request_body_minifies_json() -> None:
  from xiaobiu.har_templates import canonicalize_request_body

  out = canonicalize_request_body('{"a": 1, "b" : 2}', "application/json")
  assert out == '{"a":1,"b":2}'


def test_canonicalize_request_body_keeps_non_json_as_is() -> None:
  from xiaobiu.har_templates import canonicalize_request_body

  assert canonicalize_request_body("a=1&b=2") == "a=1&b=2"


def test_template_key_normalises_method_case() -> None:
  from xiaobiu.har_templates import _template_key

  a = _template_key("post", "https://example.com/path", "{}")
  b = _template_key("POST", "https://example.com/path", "{}")
  assert a == b


def test_template_key_keeps_path_case_sensitive() -> None:
  from xiaobiu.har_templates import _template_key

  # _normalize_url only lowercases scheme+netloc, not the path.
  assert _template_key("GET", "https://example.com/Path", "") != _template_key(
    "GET", "https://example.com/path", ""
  )


def test_decode_har_content_handles_plain_text() -> None:
  from xiaobiu.har_templates import _decode_har_content

  assert _decode_har_content({"text": "raw payload"}) == "raw payload"


def test_decode_har_content_decodes_base64() -> None:
  from xiaobiu.har_templates import _decode_har_content

  out = _decode_har_content({"text": "aGVsbG8=", "encoding": "base64"})
  assert out == "hello"


def test_extract_har_headers_picks_name_value_pairs() -> None:
  from xiaobiu.har_templates import _extract_har_headers

  headers = _extract_har_headers(
    {
      "request": {
        "headers": [
          {"name": "X-A", "value": "1"},
          {"name": "X-B", "value": "2"},
          {"name": "missing-value"},
        ]
      }
    }
  )
  assert headers == {"X-A": "1", "X-B": "2"}


def test_har_response_payload_returns_none_for_empty_text() -> None:
  from xiaobiu.har_templates import _har_response_payload

  assert _har_response_payload({"response": {"content": {"text": ""}}}) is None


def test_har_response_payload_falls_back_to_jsonp() -> None:
  from xiaobiu.har_templates import _har_response_payload

  out = _har_response_payload({"response": {"content": {"text": 'cb({"x": 1})'}}})
  assert out == {"x": 1}


def test_har_entry_is_success_requires_200_and_response_code() -> None:
  from xiaobiu.har_templates import _har_entry_is_success

  assert _har_entry_is_success(
    {"response": {"status": 200, "content": {"text": '{"responseCode": "0"}'}}}
  ) is True
  assert _har_entry_is_success(
    {"response": {"status": 500, "content": {"text": '{"responseCode": "0"}'}}}
  ) is False


def test_load_signed_templates_with_no_har_path_is_noop() -> None:
  from xiaobiu.har_templates import load_signed_templates

  client = MagicMock()
  client.har_path = None
  load_signed_templates(client)
  assert client.signed_templates == {}


def test_load_signed_templates_skips_unreadable_har(tmp_path) -> None:
  from xiaobiu.har_templates import load_signed_templates_from_har

  bad = tmp_path / "bad.har"
  bad.write_text("{not json", encoding="utf-8")
  client = MagicMock()
  client.signed_templates = {}
  load_signed_templates_from_har(client, bad)
  assert client.signed_templates == {}


def test_available_device_template_family_ids_returns_empty_when_no_posts() -> None:
  from xiaobiu.models import SignedRequestTemplate

  from xiaobiu.har_templates import available_device_template_family_ids

  client = MagicMock()
  client.signed_templates = {
    ("GET", "https://example.com/foo", ""): SignedRequestTemplate(
      method="GET", url="https://example.com/foo", body="",
    ),
  }
  assert available_device_template_family_ids(client) == []


def test_find_signed_template_returns_match() -> None:
  from xiaobiu.models import SignedRequestTemplate

  from xiaobiu.har_templates import find_signed_template

  template = SignedRequestTemplate(
    method="POST", url="https://example.com/foo", body="{}",
  )
  client = MagicMock()
  client.signed_templates = {("POST", "https://example.com/foo", "{}"): template}
  assert find_signed_template(client, "POST", "https://example.com/foo", "{}") is template
  assert find_signed_template(client, "GET", "https://example.com/foo", "{}") is None


