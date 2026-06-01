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


def test_list_families_builds_dynamic_signed_request(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  captured: dict[str, object] = {}

  class FakeResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
      return None

    def json(self) -> dict[str, object]:
      return {
        "responseCode": "0",
        "responseData": {
          "families": [{"familyId": "37790", "familyName": "我的家"}],
        },
      }

  def fake_request(method: str, url: str, **kwargs):
    captured["method"] = method
    captured["url"] = url
    captured["kwargs"] = kwargs
    return FakeResponse()

  monkeypatch.setattr(client.session, "request", fake_request)

  payload = client.list_families()

  kwargs = captured["kwargs"]
  headers = kwargs["headers"]
  assert captured["method"] == "POST"
  assert captured["url"] == FAMILY_LIST_URL
  assert kwargs["data"] == ""
  assert headers["Content-Type"] == "application/json"
  assert headers["TerminalVersion"] == client.app_user_agent
  assert headers["User-Agent"] == client.app_user_agent
  assert headers["terminalType"] == client.app_terminal_type
  assert headers["gsSign"] == _build_gs_sign(
    "/api/trade/shcss/queryAllFamily",
    headers["requestTime"],
    kwargs["data"],
  )
  assert payload["responseCode"] == "0"




def test_list_devices_builds_dynamic_signed_request(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  captured: dict[str, object] = {}

  class FakeResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
      return None

    def json(self) -> dict[str, object]:
      return {"responseCode": "0", "responseData": {"devices": []}}

  def fake_request(method: str, url: str, **kwargs):
    captured["method"] = method
    captured["url"] = url
    captured["kwargs"] = kwargs
    return FakeResponse()

  monkeypatch.setattr(client.session, "request", fake_request)

  payload = client.list_devices("37790")

  kwargs = captured["kwargs"]
  headers = kwargs["headers"]
  assert captured["method"] == "POST"
  assert captured["url"] == DEVICE_LIST_URL
  assert kwargs["data"] == '{"familyId":"37790"}'
  assert headers["Content-Type"] == "application/json"
  assert headers["gsSign"] == _build_gs_sign(
    "/api/trade/shcss/all",
    headers["requestTime"],
    kwargs["data"],
  )
  assert payload["responseCode"] == "0"




def test_request_app_api_rehydrates_shcss_before_itapig(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  calls: list[tuple[str, str]] = []
  bootstrap_calls: list[str] = []

  class RedirectResponse:
    status_code = 302
    headers = {"Location": "https://passport.suning.com/ids/login?service=itapig"}

  class SuccessResponse:
    status_code = 200
    headers: dict[str, str] = {}

  def fake_request(method: str, url: str, **kwargs):
    calls.append((method, url))
    if len(calls) == 1:
      return RedirectResponse()
    return SuccessResponse()

  monkeypatch.setattr(client.session, "request", fake_request)
  monkeypatch.setattr(client, "bootstrap_service", lambda service_name: bootstrap_calls.append(service_name))

  response = client._request_app_api(FAMILY_LIST_URL)  # noqa: SLF001

  assert response.status_code == 200
  assert calls == [("POST", FAMILY_LIST_URL), ("POST", FAMILY_LIST_URL)]
  assert bootstrap_calls == ["shcss", "itapig"]




def test_request_app_api_raises_after_failed_rebootstrap(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  bootstrap_calls: list[str] = []

  class RedirectResponse:
    status_code = 302
    headers = {"Location": "https://passport.suning.com/ids/login?service=itapig"}

  monkeypatch.setattr(client.session, "request", lambda *_args, **_kwargs: RedirectResponse())
  monkeypatch.setattr(client, "bootstrap_service", lambda service_name: bootstrap_calls.append(service_name))

  with pytest.raises(AuthenticationError, match="itapig service bootstrap failed"):
    client._request_app_api(FAMILY_LIST_URL)  # noqa: SLF001

  assert bootstrap_calls == ["shcss", "itapig"]




def test_prepare_sms_login_uses_mobile_post_form(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  cipher = SuAESCipher()
  captured: dict[str, object] = {}

  monkeypatch.setattr(client, "initialize", lambda: client.config)

  expected_inner = {
    "status": "COMPLETE",
    "data": {
      "ticket": "sms-ticket",
      "riskType": "isIarVerifyCode",
    },
  }

  class FakeResponse:
    text = json.dumps(
      {
        "_x_rdsy_resp_": cipher.encrypt(
          json.dumps(expected_inner, separators=(",", ":"), ensure_ascii=False)
        )
      },
      ensure_ascii=False,
    )

    def raise_for_status(self) -> None:
      return None

  def fake_post(url: str, **kwargs):
    captured["url"] = url
    captured["kwargs"] = kwargs
    payload = kwargs["data"]
    block = payload["_x_rdsy_block_"]
    captured["request_json"] = json.loads(cipher.decrypt(unquote_plus(block)))
    return FakeResponse()

  monkeypatch.setattr(client.session, "post", fake_post)

  result = client.prepare_sms_login("13800000000")

  request_json = captured["request_json"]
  kwargs = captured["kwargs"]
  assert captured["url"] == "https://rdsy.suning.com/rdsy/needVerifyCode.do"
  assert kwargs["data"]["callback"] == ""
  assert kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
  assert request_json["sceneId"] == MOBILE_SMS_LOGIN_SCENE_ID
  assert request_json["appCode"] == MOBILE_SMS_LOGIN_APP_CODE
  assert request_json["data"]["channel"] == MOBILE_SMS_LOGIN_CHANNEL
  assert request_json["data"]["orderChannel"] == MOBILE_SMS_LOGIN_ORDER_CHANNEL
  assert request_json["data"]["subMode"] == "11"
  assert request_json["data"]["loginTheme"] == "zn"
  assert result == expected_inner




def test_send_sms_code_uses_mobile_iar_payload(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  cipher = SuAESCipher()
  client.state.phone_number = "13800000000"
  client.state.sms_ticket = "sms-ticket"
  client.state.risk_type = "isIarVerifyCode"
  captured: dict[str, object] = {}

  expected_inner = {
    "status": "COMPLETE",
    "data": {"ticket": "login-ticket"},
  }

  class FakeResponse:
    text = json.dumps(
      {
        "_x_rdsy_resp_": cipher.encrypt(
          json.dumps(expected_inner, separators=(",", ":"), ensure_ascii=False)
        )
      },
      ensure_ascii=False,
    )

    def raise_for_status(self) -> None:
      return None

  def fake_post(url: str, **kwargs):
    captured["url"] = url
    captured["kwargs"] = kwargs
    payload = kwargs["data"]
    block = payload["_x_rdsy_block_"]
    captured["request_json"] = json.loads(cipher.decrypt(unquote_plus(block)))
    return FakeResponse()

  monkeypatch.setattr(client.session, "post", fake_post)

  result = client.send_sms_code(
    captcha=CaptchaSolution(kind="iar", value="iar-token"),
  )

  request_json = captured["request_json"]
  kwargs = captured["kwargs"]
  assert captured["url"] == "https://rdsy.suning.com/rdsy/sendCode.do"
  assert kwargs["data"]["callback"] == ""
  assert request_json["sceneId"] == MOBILE_SMS_LOGIN_SCENE_ID
  assert request_json["appCode"] == MOBILE_SMS_LOGIN_APP_CODE
  assert request_json["riskType"] == "isIarVerifyCode"
  assert request_json["uuid"] == ""
  assert request_json["code"] == "iar-token"
  assert "iarVerifyCode" not in request_json
  assert result == expected_inner
  assert client.state.login_ticket == "login-ticket"
  assert client.state.risk_type is None




def test_send_sms_code_raises_sms_rate_limited_error(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  cipher = SuAESCipher()
  client.state.phone_number = "13800000000"
  client.state.sms_ticket = "sms-ticket"
  client.state.risk_type = "isIarVerifyCode"

  expected_inner = {
    "status": "FAIL",
    "msg": "验证码发送失败，请稍后重试(00201)",
  }

  class FakeResponse:
    text = json.dumps(
      {
        "_x_rdsy_resp_": cipher.encrypt(
          json.dumps(expected_inner, separators=(",", ":"), ensure_ascii=False)
        )
      },
      ensure_ascii=False,
    )

    def raise_for_status(self) -> None:
      return None

  monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: FakeResponse())

  try:
    client.send_sms_code(
      captcha=CaptchaSolution(kind="iar", value="iar-token"),
    )
  except Exception as error:  # noqa: BLE001
    assert error.__class__.__name__ == "SmsRateLimitedError"
    assert str(error) == "验证码发送失败，请稍后重试(00201)"
  else:
    raise AssertionError("expected sms send to fail with rate limited error")




def test_login_with_sms_code_uses_mobile_post_form(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  client.state.phone_number = "13800000000"
  client.state.international_code = "0086"
  client.state.login_ticket = "login-ticket"
  captured: dict[str, object] = {}

  class FakeResponse:
    text = json.dumps({"res_message": "SUCCESS", "res_code": "0"}, ensure_ascii=False)

    def raise_for_status(self) -> None:
      return None

  def fake_post(url: str, **kwargs):
    captured["url"] = url
    captured["kwargs"] = kwargs
    return FakeResponse()

  monkeypatch.setattr(client.session, "post", fake_post)
  monkeypatch.setattr(client, "bootstrap_service", lambda service_name: {"service": service_name})

  result = client.login_with_sms_code(
    phone_number="13800000000",
    sms_code="123456",
  )

  params = captured["kwargs"]["data"]
  assert captured["url"] == "https://passport.suning.com/ids/smartLogin/sms"
  assert captured["kwargs"]["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
  assert params["sceneId"] == MOBILE_SMS_LOGIN_SCENE_ID
  assert params["terminal"] == MOBILE_SMS_LOGIN_CHANNEL
  assert params["loginChannel"] == MOBILE_SMS_LOGIN_ORDER_CHANNEL
  assert params["rememberMeType"] == MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE
  assert params["stepFlag"] == client.config.step_three_flag
  assert "callback" not in params
  assert result["res_code"] == "0"




def test_list_family_infos_parses_expected_payload_shape(monkeypatch) -> None:
  client = SuningSmartHomeClient()

  def fake_request_app_api(url: str, *, body: str = "") -> object:
    response = type("R", (), {})()
    response.json = lambda: {
      "responseCode": "0",
      "responseData": {
        "families": [
          {"familyId": "37790", "familyName": "我的家"},
        ]
      },
    }
    response.raise_for_status = lambda: None
    return response

  monkeypatch.setattr(client, "_request_app_api", fake_request_app_api)

  families = client.list_family_infos()

  assert len(families) == 1
  assert families[0].family_id == "37790"
  assert families[0].name == "我的家"




def test_keep_alive_only_queries_member_info(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  member_payload = {"code": "0", "desc": "SUCCESS"}

  monkeypatch.setattr(client, "query_member_base_info", lambda: member_payload)
  monkeypatch.setattr(
    client,
    "list_families",
    lambda: (_ for _ in ()).throw(AssertionError("keep_alive should not call list_families")),
  )

  payload = client.keep_alive()

  assert payload == {"member": member_payload}




def test_list_family_infos_accepts_id_field_from_live_api(monkeypatch) -> None:
  client = SuningSmartHomeClient()

  def fake_request_app_api(url: str, *, body: str = "") -> object:
    response = type("R", (), {})()
    response.json = lambda: {
      "responseCode": "0",
      "responseData": [
        {
          "id": 37790,
          "familyName": "139******39的家",
        }
      ],
    }
    response.raise_for_status = lambda: None
    return response

  monkeypatch.setattr(client, "_request_app_api", fake_request_app_api)

  families = client.list_family_infos()

  assert len(families) == 1
  assert families[0].family_id == "37790"
  assert families[0].name == "139******39的家"




def test_list_air_conditioner_statuses_filters_non_climate_devices(monkeypatch) -> None:
  client = SuningSmartHomeClient()

  def fake_request_app_api(url: str, *, body: str = "") -> object:
    response = type("R", (), {})()
    response.json = lambda: {
      "responseCode": "0",
      "responseData": {
        "devices": [
          {
            "id": "ac-1",
            "name": "卧室空调",
            "online": "0",
            "categoryId": "0002",
            "status": {"onlineStatus": "0"},
          },
          {
            "id": "light-1",
            "name": "客厅灯",
            "online": "1",
            "categoryId": "0001",
            "status": {"onlineStatus": "1"},
          },
        ]
      }
    }
    response.raise_for_status = lambda: None
    return response

  monkeypatch.setattr(client, "_request_app_api", fake_request_app_api)

  statuses = client.list_air_conditioner_statuses("37790")

  assert [status.device_id for status in statuses] == ["ac-1"]
  assert statuses[0].ha_climate_preview is not None




def test_normalize_air_conditioner_status_builds_ha_preview() -> None:
  client = SuningSmartHomeClient()
  raw_device = {
    "id": "000165f9b029afa2e5d8",
    "name": "惠而浦空调",
    "model": "0001000200150000",
    "online": "0",
    "gId": "1274540",
    "gName": "卧室",
    "fId": "37790",
    "time": "2024-08-18 10:47:57",
    "p1": "<font color='#999999'>已离线</font>",
    "categoryId": "0002",
    "status": {
      "refreshTime": "20251109204142",
      "onlineStatus": "0",
      "SN_POWER": "1",
      "SN_INDOORTEMP": "29.3",
      "SN_MODE": "3",
      "C_AIRHORIZONTAL": "1",
      "C_AIRVERTICAL": "1",
      "SN_TEMPERATURE": "29.3",
      "SN_FANSPEED": "0",
      "SN_ECO": "0",
      "SN_PURIFY": "0",
      "C_FRESHAIR": "0",
      "SN_ELECHEATING": "0",
    },
  }

  status = client._normalize_air_conditioner_status(raw_device)  # noqa: SLF001

  assert status.device_id == "000165f9b029afa2e5d8"
  assert status.available is False
  assert status.online is False
  assert status.summary == "已离线"
  assert status.power_on is True
  assert status.current_temperature == 29.3
  assert status.target_temperature == 29.3
  assert status.swing_horizontal is True
  assert status.swing_vertical is True
  assert status.ha_climate_preview is not None
  assert status.ha_climate_preview.entity_domain == "climate"
  assert status.ha_climate_preview.available is False
  assert status.ha_climate_preview.swing_mode == "both"
  assert status.ha_climate_preview.hvac_mode is None
  assert "设备当前离线" in " ".join(status.ha_climate_preview.notes)

  compact_payload = _air_conditioner_status_payload(status, include_raw=False)
  assert "raw_device" not in compact_payload
  assert "raw_status" not in compact_payload

  debug_payload = _air_conditioner_status_payload(status, include_raw=True)
  assert "raw_device" in debug_payload
  assert "raw_status" in debug_payload


# ---------------------------------------------------------------------------
# Task 007 — hvac_mode inference in _normalize_air_conditioner_status
# ---------------------------------------------------------------------------





def _build_client() -> SuningSmartHomeClient:
  return SuningSmartHomeClient()


def _normalize_with_status(status: dict) -> object:
  client = _build_client()
  device = {
    "id": "000165f9b029afa2e5d8",
    "name": "客厅空调",
    "modelId": "0001000200150000",
    "fId": "37790",
    "categoryId": "0002",
    "online": "1",
    "status": {"onlineStatus": "1", **status},
  }
  return client._normalize_air_conditioner_status(device)


def test_normalize_hvac_mode_off_when_power_zero() -> None:
  status = _normalize_with_status({"C_POWER": "0"})
  assert status.hvac_mode == "off"




def test_normalize_hvac_mode_cool_heat_dry_fan_auto() -> None:
  cases = {
    "1": "cool",
    "2": "heat",
    "3": "fan_only",
    "4": "dry",
    "6": "auto",
  }
  for raw, expected in cases.items():
    status = _normalize_with_status({"C_POWER": "1", "C_MODE": raw})
    assert status.hvac_mode == expected, f"C_MODE={raw}"




def test_normalize_hvac_mode_uses_sn_prefix_fallback() -> None:
  status = _normalize_with_status({"SN_POWER": "1", "SN_MODE": "1"})
  assert status.hvac_mode == "cool"




def test_normalize_hvac_mode_none_when_no_fields() -> None:
  assert _normalize_with_status({}).hvac_mode is None




def test_normalize_hvac_mode_none_when_power_on_but_mode_missing() -> None:
  assert _normalize_with_status({"C_POWER": "1"}).hvac_mode is None




def test_normalize_hvac_mode_unknown_mode_value_keeps_none() -> None:
  # C_MODE=7 is unassigned; do not guess.
  assert _normalize_with_status({"C_POWER": "1", "C_MODE": "7"}).hvac_mode is None




def test_normalize_hvac_mode_quick() -> None:
  assert _normalize_with_status({"C_POWER": "1", "C_MODE": "5"}).hvac_mode == "quick"




def test_normalize_ha_climate_preview_notes_drop_placeholder() -> None:
  status = _normalize_with_status(
    {"C_POWER": "1", "C_MODE": "1", "C_ELECHEATING": "0"},
  )
  joined = " ".join(status.ha_climate_preview.notes or [])
  assert "模式枚举尚未确认" not in joined
  assert "C_ELECHEATING" in joined


# ---------------------------------------------------------------------------
# Task 008 — new CLI subcommands
# ---------------------------------------------------------------------------




def test_resolve_ac_target_reads_model_field_from_list_devices(monkeypatch) -> None:
  client = SuningSmartHomeClient()
  device = {
    "id": "000165f9b029afa2e5d8",
    "name": "惠而浦空调",
    "model": "0001000200150000",  # list_devices uses "model", not "modelId"
    "fId": "37790",
  }
  monkeypatch.setattr(client, "get_device", lambda *_, **__: device)
  resolved_id, resolved_model = client._resolve_ac_target("37790", "000165f9b029afa2e5d8")
  assert resolved_id == "000165f9b029afa2e5d8"
  assert resolved_model == "0001000200150000"
