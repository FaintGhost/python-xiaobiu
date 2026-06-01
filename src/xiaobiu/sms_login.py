"""SMS-based login flow against the Suning passport service.

Functions take ``client`` by duck type — they only require ``client.session``,
``client.timeout``, ``client.config``, ``client.state`` and ``client.suaes``.
They never import :class:`SuningSmartHomeClient` to avoid circular imports.
"""

from __future__ import annotations

import json
import time
from typing import Any

from . import ac_status  # noqa: F401  (used transitively via client.bootstrap_service)
from .crypto import rsa_encrypt_base64
from .exceptions import (
  AuthenticationError,
  CaptchaRequiredError,
  SmsRateLimitedError,
  SuningError,
)
from .models import CaptchaSolution, LoginPageConfig
from .parsers import (
  _extract_business_error_code,
  extract_risk_context_script_urls,
  parse_jsonp_or_json,
  parse_login_page_config,
)

DEFAULT_LOGIN_URL = "https://passport.suning.com/ids/login"
DEFAULT_TARGET_URL = "https://www.suning.com/"

MOBILE_SMS_LOGIN_APP_CODE = "7b8e1574afdd47a8a14766c4f003cff7"
MOBILE_SMS_LOGIN_SCENE_ID = "PASSPORT_XIAOBIU"
MOBILE_SMS_LOGIN_CHANNEL = "MOBILE"
MOBILE_SMS_LOGIN_ORDER_CHANNEL = "208000201090"
MOBILE_SMS_LOGIN_THEME = "zn"
MOBILE_SMS_LOGIN_APP_VERSION = "6.4.5"
MOBILE_SMS_LOGIN_SUB_MODE = "11"
MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE = "app"

SMS_RATE_LIMIT_ERROR_CODE = "00201"

RDSY_NEED_VERIFY_URL = "https://rdsy.suning.com/rdsy/needVerifyCode.do"
RDSY_SEND_CODE_URL = "https://rdsy.suning.com/rdsy/sendCode.do"
IAR_TICKET_URL = "https://passport.suning.com/ids/iarVerifyCodeTicket"
SMS_LOGIN_URL = "https://passport.suning.com/ids/smartLogin/sms"

DEFAULT_LOGIN_PAGE_CONFIG = LoginPageConfig(
  login_pbk=(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQComqoAyvbCqO1EGsADwfNTWFQIUbm8"
    "CLdeb9TgjGLcz95mAo204SqTYdSEUxFsOnPfROOTxhkhfjbRxBV4/xjS06Y+kkUdiMG"
    "FtABIxRQHQIh0LrVvEZQs4NrixxcPI+b1bpE0gO/GAFSNWm9ejhZGj7UnqiHphnSJAVQ"
    "Nz2lgowIDAQAB"
  ),
  rdsy_key=(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDZnlkciI+qxNATzQOOcU8rxtfJxlbj"
    "RKEhoz1WhuAFuCe6ZHEh85UjGiG0FN0oBCKoC4aprTlzNDEr/cU2bzTJELhs9xoU80Um"
    "364GY0zbMr1qnnSouyv0Wb/sgrB/cTDmw8HNiX77mCmX+R4Un/6Xj3BBpm52CHn3RXI9"
    "HeE/xwIDAQAB"
  ),
  rdsy_app_code="9FAD2DDEFE754D604779F7BB8264C80F",
  step_flag="8763EC7BB5D7EEE18EDD1E4BD59A1679",
  step_two_flag="3D58885D2B0CB135703770C03852E8CB",
  step_three_flag="08DD83216388DA0A29B5B3CEE0CC0E6F",
  rdsy_scene_id="PASSPORT",
  rdsy_scene_id_yghk="PASSPORT_YGHK",
  channel="PC",
  check_account_key=(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCOuozMgVH/glMcCOIDKjXP83zDmgi6"
    "hKvwB9VLQG6RWcxm/lNmB/Uq3LGdKUnm+JBFy1GeHA8oNKLFROF/ebzSqr6kOkuSsAZm"
    "cvsvgaigD7cSzIipdfJpE3bZd9y7X8Mq+uDhNKpvlH9lR+OmTgMFAKq8w6QMYY+ksHjW"
    "INSDIwIDAQAB"
  ),
)


def _rdsy_headers() -> dict[str, str]:
  return {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": DEFAULT_LOGIN_URL,
  }


def initialize(client: Any) -> LoginPageConfig:
  response = client.session.get(DEFAULT_LOGIN_URL, timeout=client.timeout)
  response.raise_for_status()
  try:
    client.config = parse_login_page_config(response.text)
  except SuningError:
    client.config = DEFAULT_LOGIN_PAGE_CONFIG
  script_urls = extract_risk_context_script_urls(response.text)
  if script_urls:
    client.risk_context_script_urls = script_urls
  client._touch_state()
  return client.config


def prepare_sms_login(
  client: Any,
  phone_number: str,
  *,
  international_code: str = "0086",
) -> dict[str, Any]:
  initialize(client)
  client.state.phone_number = phone_number
  client.state.international_code = international_code
  request_body = _build_prepare_sms_login_payload(
    client,
    phone_number=phone_number,
    international_code=international_code,
  )
  payload = {
    "_x_rdsy_block_": client.suaes.encrypt(
      json.dumps(request_body, separators=(",", ":"), ensure_ascii=False)
    ),
    "callback": _rdsy_callback(client, international_code, "needVerifyCode"),
  }
  response = client.session.post(
    RDSY_NEED_VERIFY_URL,
    data=payload,
    timeout=client.timeout,
    headers=_rdsy_headers(),
  )
  response.raise_for_status()
  outer = parse_jsonp_or_json(response.text)
  inner = _decrypt_rdsy_response(client, outer)
  if inner.get("status") != "COMPLETE":
    raise SuningError(inner.get("msg") or "failed to prepare sms login")
  client.state.sms_ticket = inner["data"].get("ticket")
  client.state.risk_type = inner["data"].get("riskType")
  client._touch_state()
  return inner


def send_sms_code(
  client: Any,
  phone_number: str | None = None,
  *,
  international_code: str | None = None,
  captcha: CaptchaSolution | None = None,
) -> dict[str, Any]:
  target_phone = phone_number or client.state.phone_number
  if not target_phone:
    raise SuningError("phone number is required")
  area_code = international_code or client.state.international_code
  if not client.state.sms_ticket or not client.state.risk_type:
    prepare_sms_login(client, target_phone, international_code=area_code)
  if (
    client.state.risk_type
    and client.state.risk_type != "isNullVerifyCode"
    and not captcha
  ):
    raise CaptchaRequiredError(
      client.state.risk_type,
      "captcha token is required before sending sms code",
      client.state.sms_ticket,
    )
  params = _build_send_sms_code_payload(
    client,
    phone_number=target_phone,
    international_code=area_code,
    captcha=captcha,
  )
  payload = {
    "_x_rdsy_block_": client.suaes.encrypt(
      json.dumps(params, separators=(",", ":"), ensure_ascii=False)
    ),
    "callback": _rdsy_callback(client, area_code, "sendCode"),
  }
  response = client.session.post(
    RDSY_SEND_CODE_URL,
    data=payload,
    timeout=client.timeout,
    headers=_rdsy_headers(),
  )
  response.raise_for_status()
  outer = parse_jsonp_or_json(response.text)
  inner = _decrypt_rdsy_response(client, outer)
  if inner.get("status") == "COMPLETE":
    client.state.login_ticket = inner["data"].get("ticket")
    client.state.risk_type = None
    client._touch_state()
    return inner
  if inner.get("code") == "R0004":
    data = inner.get("data") or {}
    client.state.sms_ticket = data.get("ticket") or client.state.sms_ticket
    client.state.risk_type = data.get("riskType") or client.state.risk_type
    client._touch_state()
    raise CaptchaRequiredError(
      client.state.risk_type or "unknown",
      inner.get("msg") or "captcha is required again",
      client.state.sms_ticket,
    )
  message = inner.get("msg") or "failed to send sms code"
  error_code = _extract_business_error_code(
    inner.get("code"),
    inner.get("resCode"),
    inner.get("errCode"),
    inner.get("errorCode"),
    message,
  )
  if error_code == SMS_RATE_LIMIT_ERROR_CODE:
    raise SmsRateLimitedError(message, error_code=error_code)
  raise SuningError(message)


def request_iar_verify_code_ticket(client: Any, phone_number: str) -> str:
  response = client.session.post(
    IAR_TICKET_URL,
    data={
      "deviceId": "",
      "dfpToken": client.state.dfp_token,
      "username": phone_number,
    },
    timeout=client.timeout,
    headers=_rdsy_headers(),
  )
  response.raise_for_status()
  data = response.json()
  if str(data.get("result")).lower() != "true" or not data.get("ticket"):
    raise SuningError("申请 IAR 验证 ticket 失败")
  return data["ticket"]


def login_with_sms_code(
  client: Any,
  *,
  phone_number: str | None = None,
  sms_code: str,
  international_code: str | None = None,
) -> dict[str, Any]:
  target_phone = phone_number or client.state.phone_number
  if not target_phone:
    raise SuningError("phone number is required")
  area_code = international_code or client.state.international_code
  if not client.state.login_ticket:
    raise SuningError("login ticket is missing, send sms code first")
  params = _build_sms_login_payload(
    client,
    phone_number=target_phone,
    sms_code=sms_code,
    international_code=area_code,
  )
  response = client.session.post(
    SMS_LOGIN_URL,
    data=params,
    timeout=client.timeout,
    headers=_rdsy_headers(),
  )
  response.raise_for_status()
  data = parse_jsonp_or_json(response.text)
  if not _is_login_success(data):
    raise AuthenticationError(
      data.get("msg") or data.get("res_message") or "sms login failed"
    )
  client.state.login_response = data
  client._touch_state()
  client.bootstrap_service("shcss")
  client.bootstrap_service("itapig")
  return data


# ---------------------------------------------------------------------------
# Internal helpers (exposed for the test suite)
# ---------------------------------------------------------------------------


def _uses_mobile_sms_login(international_code: str) -> bool:
  return international_code == "0086"


def _mobile_sms_login_data(client: Any, phone_number: str) -> dict[str, str]:
  return {
    "mode": "1",
    "subMode": MOBILE_SMS_LOGIN_SUB_MODE,
    "channel": MOBILE_SMS_LOGIN_CHANNEL,
    "dfpToken": client.state.dfp_token,
    "orderChannel": MOBILE_SMS_LOGIN_ORDER_CHANNEL,
    "custType": "0",
    "ways": "duanxindl",
    "userName": phone_number,
    "source": "",
    "token": "",
    "detect": client.state.detect,
    "referenceURL": "",
    "miniType": "",
    "result": "",
    "cntctMobileNum": phone_number,
    "loginTheme": MOBILE_SMS_LOGIN_THEME,
    "appVersion": MOBILE_SMS_LOGIN_APP_VERSION,
    "openId": "",
  }


def _build_prepare_sms_login_payload(
  client: Any,
  *,
  phone_number: str,
  international_code: str,
) -> dict[str, Any]:
  if _uses_mobile_sms_login(international_code):
    return {
      "sceneId": MOBILE_SMS_LOGIN_SCENE_ID,
      "stepFlag": client.config.step_flag,
      "appCode": MOBILE_SMS_LOGIN_APP_CODE,
      "data": _mobile_sms_login_data(client, phone_number),
    }
  return {
    "sceneId": _scene_id(client, international_code),
    "stepFlag": client.config.step_flag,
    "appCode": client.config.rdsy_app_code,
    "data": {
      "ways": "duanxindl",
      "channel": client.config.channel,
      "orderChannel": _channel(international_code),
      "dfpToken": client.state.dfp_token,
      "detect": client.state.detect,
      "loginTheme": "defaultTheme",
      "referenceURL": DEFAULT_LOGIN_URL,
      "userName": phone_number,
      "cntctMobileNum": phone_number,
      "mode": "1",
      "subMode": "4",
    },
  }


def _build_send_sms_code_payload(
  client: Any,
  *,
  phone_number: str,
  international_code: str,
  captcha: CaptchaSolution | None,
) -> dict[str, Any]:
  if _uses_mobile_sms_login(international_code):
    params: dict[str, Any] = {
      "sceneId": MOBILE_SMS_LOGIN_SCENE_ID,
      "stepFlag": client.config.step_two_flag,
      "appCode": MOBILE_SMS_LOGIN_APP_CODE,
      "riskType": client.state.risk_type or "",
      "phoneNum": rsa_encrypt_base64(phone_number, client.config.rdsy_key),
      "ticket": client.state.sms_ticket or "",
      "code": "",
      "uuid": "",
      "data": _mobile_sms_login_data(client, phone_number),
    }
    if captcha:
      params.update(_mobile_captcha_fields(captcha))
    return params
  params = {
    "sceneId": _scene_id(client, international_code),
    "stepFlag": client.config.step_two_flag,
    "appCode": client.config.rdsy_app_code,
    "riskType": client.state.risk_type or "",
    "phoneNum": rsa_encrypt_base64(phone_number, client.config.rdsy_key),
    "internationalCode": international_code,
    "callback": _jsonp_callback("sendCode"),
    "ticket": client.state.sms_ticket or "",
    "code": "",
    "uuid": "",
    "data": {
      "ways": "duanxindl",
      "channel": client.config.channel,
      "orderChannel": _channel(international_code),
      "dfpToken": client.state.dfp_token,
      "detect": client.state.detect,
      "loginTheme": "defaultTheme",
      "userName": phone_number,
      "cntctMobileNum": phone_number,
      "checkAliasName": "0",
      "referenceURL": DEFAULT_LOGIN_URL,
    },
  }
  if captcha:
    params.update(_captcha_fields(captcha))
  return params


def _build_sms_login_payload(
  client: Any,
  *,
  phone_number: str,
  sms_code: str,
  international_code: str,
) -> dict[str, str]:
  if _uses_mobile_sms_login(international_code):
    return {
      "appVersion": MOBILE_SMS_LOGIN_APP_VERSION,
      "detect": client.state.detect,
      "dfpToken": client.state.dfp_token,
      "jsonViewType": "true",
      "loginChannel": MOBILE_SMS_LOGIN_ORDER_CHANNEL,
      "phoneNumber": rsa_encrypt_base64(phone_number, client.config.check_account_key),
      "rememberMe": "true",
      "rememberMeType": MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE,
      "sceneId": MOBILE_SMS_LOGIN_SCENE_ID,
      "smsCode": sms_code,
      "stepFlag": client.config.step_three_flag,
      "terminal": MOBILE_SMS_LOGIN_CHANNEL,
      "ticket": client.state.login_ticket,
    }
  return {
    "callback": _jsonp_callback("smsLogin"),
    "ticket": client.state.login_ticket,
    "phoneNumber": rsa_encrypt_base64(phone_number, client.config.check_account_key),
    "internationalCode": international_code,
    "channel": client.config.channel,
    "smsCode": sms_code,
    "rememberMe": "true",
    "type": "1",
    "sceneId": _scene_id(client, international_code),
    "targetUrl": DEFAULT_TARGET_URL,
    "service": "",
    "detect": client.state.detect,
    "secondFlag": "100000000010",
    "dfpToken": client.state.dfp_token,
    "terminal": client.config.channel,
    "createChannel": _channel(international_code),
    "loginChannel": _channel(international_code),
    "smsCodeVersion": "1.0",
    "jsonViewType": "true",
    "viewType": "json",
    "loginOrRegFlag": "0",
    "version": "2.0",
  }


def _decrypt_rdsy_response(client: Any, outer_payload: dict[str, Any]) -> dict[str, Any]:
  encrypted = outer_payload.get("_x_rdsy_resp_")
  if not encrypted:
    raise SuningError("missing _x_rdsy_resp_ in rdsy response")
  return json.loads(client.suaes.decrypt(encrypted))


def _captcha_fields(captcha: CaptchaSolution) -> dict[str, str]:
  mapping = {
    "iar": {
      "uuid": "iarVerifyCode",
      "iarVerifyCode": captcha.value,
      "code": captcha.value,
    },
    "slide": {
      "uuid": "sillerVerifyCode",
      "sillerCode": captcha.value,
      "code": captcha.value,
    },
    "image": {
      "uuid": "19da7909-9b5d-4aee-99ee-28016002eaac",
      "imgCode": captcha.value,
      "code": captcha.value,
    },
  }
  if captcha.kind not in mapping:
    raise SuningError(f"unsupported captcha kind: {captcha.kind}")
  return mapping[captcha.kind]


def _mobile_captcha_fields(captcha: CaptchaSolution) -> dict[str, str]:
  mapping = {
    "iar": {
      "uuid": "",
      "code": captcha.value,
    },
    "slide": {
      "uuid": "sillerVerifyCode",
      "sillerCode": captcha.value,
      "code": captcha.value,
    },
    "image": {
      "uuid": "19da7909-9b5d-4aee-99ee-28016002eaac",
      "imgCode": captcha.value,
      "code": captcha.value,
    },
  }
  if captcha.kind not in mapping:
    raise SuningError(f"unsupported captcha kind: {captcha.kind}")
  return mapping[captcha.kind]


def _scene_id(client: Any, international_code: str) -> str:
  if international_code == "00852":
    return client.config.rdsy_scene_id_yghk
  return client.config.rdsy_scene_id


def _channel(international_code: str) -> str:
  if international_code == "00852":
    return "208000104024"
  return "208000103001"


def _jsonp_callback(prefix: str) -> str:
  return f"{prefix}_{int(time.time() * 1000)}"


def _rdsy_callback(client: Any, international_code: str, prefix: str) -> str:
  if _uses_mobile_sms_login(international_code):
    return ""
  return _jsonp_callback(prefix)


def _is_login_success(payload: dict[str, Any]) -> bool:
  return bool(
    payload.get("success")
    or (
      payload.get("res_message") == "SUCCESS"
      and str(payload.get("res_code")) == "0"
    )
  )


__all__ = [
  "DEFAULT_LOGIN_PAGE_CONFIG",
  "DEFAULT_LOGIN_URL",
  "DEFAULT_TARGET_URL",
  "IAR_TICKET_URL",
  "MOBILE_SMS_LOGIN_APP_CODE",
  "MOBILE_SMS_LOGIN_APP_VERSION",
  "MOBILE_SMS_LOGIN_CHANNEL",
  "MOBILE_SMS_LOGIN_ORDER_CHANNEL",
  "MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE",
  "MOBILE_SMS_LOGIN_SCENE_ID",
  "MOBILE_SMS_LOGIN_SUB_MODE",
  "MOBILE_SMS_LOGIN_THEME",
  "RDSY_NEED_VERIFY_URL",
  "RDSY_SEND_CODE_URL",
  "SMS_LOGIN_URL",
  "SMS_RATE_LIMIT_ERROR_CODE",
  "initialize",
  "login_with_sms_code",
  "prepare_sms_login",
  "request_iar_verify_code_ticket",
  "send_sms_code",
]
