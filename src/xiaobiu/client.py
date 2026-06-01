"""SuningSmartHomeClient — thin façade over the xiaobiu sub-modules.

The implementation lives in:

- :mod:`.sms_login` — passport / SMS login flow
- :mod:`.har_templates` — HAR-backed signed request cache
- :mod:`.ac_status` — family / device / AC state surface
- :mod:`.ac_control` — air-conditioner command dispatch
- :mod:`.app_api` — gsSign / app-api plumbing
- :mod:`.parsers` — jsonp / login-page parsing
- :mod:`.cli` — ``xiaobiucli`` entry point

All public symbols historically re-exported from this module are
re-exported below for backward compatibility.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import requests
from requests.cookies import create_cookie

from . import (
  ac_control,
  ac_status,
  app_api,
  exceptions,
  har_templates,
  parsers,
  persistence,
  sms_login,
)
from .crypto import SuAESCipher
from .models import (
  AirConditionerStatus,
  AuthState,
  CaptchaSolution,
  FanSpeed,
  HvacMode,
  LoginPageConfig,
  PanelTemplate,
  PersistedSessionState,
  PresetMode,
  SerializedCookie,
  SignedRequestTemplate,
  SwingMode,
  Timer,
)

if TYPE_CHECKING:  # pragma: no cover
  from .cli import main as _main  # noqa: F401

DEFAULT_TIMEOUT = 20.0
DEFAULT_USER_AGENT = (
  "Mozilla/5.0 (X11; Linux x86_64) "
  "AppleWebKit/537.36 (KHTML, like Gecko) "
  "Chrome/134.0.0.0 Safari/537.36"
)


# Back-compat alias.  These are intentionally *the same class objects* as
# the canonical ``exceptions`` module definitions so that ``isinstance``
# and ``pytest.raises`` checks across modules keep working.  We do
# not subclass them here.
SuningError = exceptions.SuningError
CaptchaRequiredError = exceptions.CaptchaRequiredError
SmsRateLimitedError = exceptions.SmsRateLimitedError
AuthenticationError = exceptions.AuthenticationError


# Backward-compat module-level constants previously inlined in client.py.
DEVICE_LIST_URL = ac_status.DEVICE_LIST_URL
FAMILY_LIST_URL = ac_status.FAMILY_LIST_URL
OPENSH_GET_KEY_URL = ac_status.OPENSH_GET_KEY_URL
MEMBER_BASE_INFO_URL = ac_status.MEMBER_BASE_INFO_URL
SERVICE_BOOTSTRAP_URLS = ac_status.SERVICE_BOOTSTRAP_URLS
AIR_CONDITIONER_CATEGORY_ID = ac_status.AIR_CONDITIONER_CATEGORY_ID
AIR_CONDITIONER_NAME_KEYWORD = ac_status.AIR_CONDITIONER_NAME_KEYWORD

DEFAULT_LOGIN_URL = sms_login.DEFAULT_LOGIN_URL
DEFAULT_TARGET_URL = sms_login.DEFAULT_TARGET_URL
MOBILE_SMS_LOGIN_APP_CODE = sms_login.MOBILE_SMS_LOGIN_APP_CODE
MOBILE_SMS_LOGIN_SCENE_ID = sms_login.MOBILE_SMS_LOGIN_SCENE_ID
MOBILE_SMS_LOGIN_CHANNEL = sms_login.MOBILE_SMS_LOGIN_CHANNEL
MOBILE_SMS_LOGIN_ORDER_CHANNEL = sms_login.MOBILE_SMS_LOGIN_ORDER_CHANNEL
MOBILE_SMS_LOGIN_THEME = sms_login.MOBILE_SMS_LOGIN_THEME
MOBILE_SMS_LOGIN_APP_VERSION = sms_login.MOBILE_SMS_LOGIN_APP_VERSION
MOBILE_SMS_LOGIN_SUB_MODE = sms_login.MOBILE_SMS_LOGIN_SUB_MODE
MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE = sms_login.MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE
SMS_RATE_LIMIT_ERROR_CODE = sms_login.SMS_RATE_LIMIT_ERROR_CODE
DEFAULT_LOGIN_PAGE_CONFIG = sms_login.DEFAULT_LOGIN_PAGE_CONFIG

DEFAULT_APP_USER_AGENT = app_api.DEFAULT_APP_USER_AGENT
DEFAULT_APP_TERMINAL_TYPE = app_api.DEFAULT_APP_TERMINAL_TYPE
DEFAULT_APP_ACCEPT_LANGUAGE = app_api.DEFAULT_APP_ACCEPT_LANGUAGE
APP_API_GS_SIGN_SECRET = app_api.APP_API_GS_SIGN_SECRET

SUCCESS_RESPONSE_CODES = app_api.SUCCESS_RESPONSE_CODES

# Re-exports for the public parsing / signing surface.
parse_jsonp_or_json = parsers.parse_jsonp_or_json
parse_login_page_config = parsers.parse_login_page_config
extract_risk_context_script_urls = parsers.extract_risk_context_script_urls
_extract_business_error_code = parsers._extract_business_error_code

_build_gs_sign = app_api.build_gs_sign
_build_gs_sign_payload = app_api.build_gs_sign_payload
_canonicalize_request_body = app_api.canonicalize_request_body
_normalize_url = app_api.normalize_url
_serialize_cookie = persistence.serialize_cookie
_restore_cookie = persistence.restore_cookie

# Internal SMS-login helpers (re-exported for the existing test suite).
_uses_mobile_sms_login = sms_login._uses_mobile_sms_login
_mobile_sms_login_data = sms_login._mobile_sms_login_data
_build_prepare_sms_login_payload = sms_login._build_prepare_sms_login_payload
_build_send_sms_code_payload = sms_login._build_send_sms_code_payload
_build_sms_login_payload = sms_login._build_sms_login_payload
_decrypt_rdsy_response = sms_login._decrypt_rdsy_response
_captcha_fields = sms_login._captcha_fields
_mobile_captcha_fields = sms_login._mobile_captcha_fields
_scene_id = sms_login._scene_id
_channel = sms_login._channel
_jsonp_callback = sms_login._jsonp_callback
_rdsy_callback = sms_login._rdsy_callback
_is_login_success = sms_login._is_login_success

# Internal HAR / status / AC helpers (re-exported for the existing test suite).
_decode_har_content = har_templates._decode_har_content
_extract_har_headers = har_templates._extract_har_headers
_har_response_payload = har_templates._har_response_payload
_har_entry_is_success = har_templates._har_entry_is_success
_template_key = har_templates._template_key

_coalesce = ac_status._coalesce
_parse_bool_flag = ac_status._parse_bool_flag
_parse_float_value = ac_status._parse_float_value
_strip_html_text = ac_status._strip_html_text
_infer_swing_mode = ac_status._infer_swing_mode
_is_air_conditioner_device = ac_status._is_air_conditioner_device
_build_ha_climate_preview = ac_status._build_ha_climate_preview


# CLI re-exports — functions live in ``cli.py``; we re-export the
# symbols the legacy test suite (and ``xiaobiu.__init__``) import from
# ``xiaobiu.client``.
from .cli import (  # noqa: E402  (intentional late import)
  _air_conditioner_status_payload,
  _build_captcha_from_args,
  _build_parser,
  _captcha_kind_from_risk_type,
  _client_from_args,
  _interactive_login,
  _obtain_iar_captcha_result,
  _print_payload,
  _prompt_nonempty,
  _send_sms_with_optional_prompt,
  main,
)


class SuningSmartHomeClient:
  def __init__(
    self,
    *,
    state_path: str | Path | None = None,
    har_path: str | Path | None = None,
    load_state: bool = True,
    detect: str | None = None,
    dfp_token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    app_user_agent: str = DEFAULT_APP_USER_AGENT,
    app_terminal_type: str = DEFAULT_APP_TERMINAL_TYPE,
  ) -> None:
    self.timeout = timeout
    self.state_path = Path(state_path) if state_path else None
    self.har_path = Path(har_path) if har_path else None
    self.app_user_agent = app_user_agent
    self.app_terminal_type = app_terminal_type
    self.session = requests.Session()
    self.session.headers.update(
      {
        "Accept": "*/*",
        "User-Agent": user_agent,
      }
    )
    self.suaes = SuAESCipher()
    self.config = DEFAULT_LOGIN_PAGE_CONFIG
    self.state = AuthState()
    self.signed_templates: dict[tuple[str, str, str], SignedRequestTemplate] = {}
    self.risk_context_script_urls: list[str] = []
    if detect:
      self.state.detect = detect
    if dfp_token:
      self.state.dfp_token = dfp_token
    if load_state and self.state_path and self.state_path.exists():
      self.load_state()
    if self.har_path:
      self.load_signed_templates()

  # ------------------------------------------------------------------
  # State management
  # ------------------------------------------------------------------

  def update_risk_context(self, *, detect: str | None = None, dfp_token: str | None = None) -> None:
    if detect:
      self.state.detect = detect
    if dfp_token:
      self.state.dfp_token = dfp_token
    self._touch_state()

  def reset_sms_login_state(self) -> None:
    self.state.risk_type = None
    self.state.sms_ticket = None
    self.state.login_ticket = None
    self._touch_state()

  def save_state(self) -> None:
    if not self.state_path:
      return
    self.state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = PersistedSessionState(
      state=self.state,
      cookies=[_serialize_cookie(cookie) for cookie in self.session.cookies],
    )
    self.state_path.write_text(
      json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
      encoding="utf-8",
    )

  def load_state(self) -> None:
    if not self.state_path or not self.state_path.exists():
      return
    payload = PersistedSessionState.model_validate_json(
      self.state_path.read_text(encoding="utf-8")
    )
    self.state = payload.state
    self.session.cookies.clear()
    for serialized_cookie in payload.cookies:
      self.session.cookies.set_cookie(_restore_cookie(serialized_cookie))

  def _touch_state(self) -> None:
    self.state.updated_at = time.time()
    self.save_state()

  # ------------------------------------------------------------------
  # SMS login (thin forwards)
  # ------------------------------------------------------------------

  def initialize(self) -> LoginPageConfig:
    return sms_login.initialize(self)

  def prepare_sms_login(self, phone_number: str, *, international_code: str = "0086") -> dict[str, Any]:
    return sms_login.prepare_sms_login(self, phone_number, international_code=international_code)

  def send_sms_code(
    self,
    phone_number: str | None = None,
    *,
    international_code: str | None = None,
    captcha: CaptchaSolution | None = None,
  ) -> dict[str, Any]:
    return sms_login.send_sms_code(
      self, phone_number, international_code=international_code, captcha=captcha,
    )

  def request_iar_verify_code_ticket(self, phone_number: str) -> str:
    return sms_login.request_iar_verify_code_ticket(self, phone_number)

  def login_with_sms_code(
    self,
    *,
    phone_number: str | None = None,
    sms_code: str,
    international_code: str | None = None,
  ) -> dict[str, Any]:
    return sms_login.login_with_sms_code(
      self,
      phone_number=phone_number,
      sms_code=sms_code,
      international_code=international_code,
    )

  # ------------------------------------------------------------------
  # Service bootstrap / keep alive (thin forwards to ac_status)
  # ------------------------------------------------------------------

  def bootstrap_service(self, service_name: str) -> dict[str, Any]:
    return ac_status.bootstrap_service(self, service_name)

  def query_member_base_info(self) -> dict[str, Any]:
    return ac_status.query_member_base_info(self)

  def keep_alive(self) -> dict[str, Any]:
    member_info = self.query_member_base_info()
    return {"member": member_info}

  # ------------------------------------------------------------------
  # app-api plumbing (kept as thin forwards so the legacy
  # ``client._request_app_api`` / ``_decode_app_api_response`` names
  # keep working)
  # ------------------------------------------------------------------

  def _build_app_api_headers(self, url: str, *, body: str) -> dict[str, str]:
    return app_api.build_app_api_headers(
      url,
      body=body,
      user_agent=self.app_user_agent,
      terminal_type=self.app_terminal_type,
    )

  def _request_app_api(self, url: str, *, body: str = "") -> requests.Response:
    payload = _canonicalize_request_body(body, "application/json")
    response = app_api.request_app_api(
      self,
      url,
      body=payload,
      bootstrap=self.bootstrap_service,
    )
    return response

  def _decode_app_api_response(self, response: requests.Response, *, action: str) -> dict[str, Any]:
    return app_api.decode_app_api_response(response, action=action)

  def _is_login_redirect(self, response: requests.Response) -> bool:
    return app_api.is_login_redirect(response)

  # ------------------------------------------------------------------
  # Family / device / AC state (thin forwards to ac_status)
  # ------------------------------------------------------------------

  def list_families(self) -> dict[str, Any]:
    return ac_status.list_families(self)

  def list_family_infos(self) -> list:
    return ac_status.list_family_infos(self)

  def list_devices(self, family_id: str | int) -> dict[str, Any]:
    return ac_status.list_devices(self, family_id)

  def get_device(self, family_id: str | int, *, device_id: str | int | None = None) -> dict[str, Any]:
    return ac_status.get_device(self, family_id, device_id=device_id)

  def get_air_conditioner_status(
    self,
    family_id: str | int,
    *,
    device_id: str | int | None = None,
  ) -> AirConditionerStatus:
    return ac_status.get_air_conditioner_status(self, family_id, device_id=device_id)

  def list_air_conditioner_statuses(self, family_id: str | int) -> list[AirConditionerStatus]:
    return ac_status.list_air_conditioner_statuses(self, family_id)

  def _normalize_air_conditioner_status(self, device: dict[str, Any]) -> AirConditionerStatus:
    return ac_status._normalize_air_conditioner_status(device)

  def _is_air_conditioner_device(self, device: dict[str, Any]) -> bool:
    return ac_status._is_air_conditioner_device(device)

  def _build_ha_climate_preview(self, status: AirConditionerStatus) -> Any:
    return ac_status._build_ha_climate_preview(status)

  def _infer_hvac_mode(self, *, power_on: bool | None, mode_raw: Any) -> HvacMode | None:
    return ac_status.infer_hvac_mode(power_on=power_on, mode_raw=mode_raw)

  # SMS-login private helpers (re-exported for the test suite).
  def _captcha_fields(self, captcha: CaptchaSolution) -> dict[str, str]:
    return sms_login._captcha_fields(captcha)

  def _mobile_captcha_fields(self, captcha: CaptchaSolution) -> dict[str, str]:
    return sms_login._mobile_captcha_fields(captcha)

  def _decrypt_rdsy_response(self, outer_payload: dict[str, Any]) -> dict[str, Any]:
    return sms_login._decrypt_rdsy_response(self, outer_payload)

  def _is_login_success(self, payload: dict[str, Any]) -> bool:
    return sms_login._is_login_success(payload)

  def _uses_mobile_sms_login(self, international_code: str) -> bool:
    return sms_login._uses_mobile_sms_login(international_code)

  def _mobile_sms_login_data(self, phone_number: str) -> dict[str, str]:
    return sms_login._mobile_sms_login_data(self, phone_number)

  def _build_prepare_sms_login_payload(
    self,
    *,
    phone_number: str,
    international_code: str,
  ) -> dict[str, Any]:
    return sms_login._build_prepare_sms_login_payload(
      self,
      phone_number=phone_number,
      international_code=international_code,
    )

  def _build_send_sms_code_payload(
    self,
    *,
    phone_number: str,
    international_code: str,
    captcha: CaptchaSolution | None,
  ) -> dict[str, Any]:
    return sms_login._build_send_sms_code_payload(
      self,
      phone_number=phone_number,
      international_code=international_code,
      captcha=captcha,
    )

  def _build_sms_login_payload(
    self,
    *,
    phone_number: str,
    sms_code: str,
    international_code: str,
  ) -> dict[str, str]:
    return sms_login._build_sms_login_payload(
      self,
      phone_number=phone_number,
      sms_code=sms_code,
      international_code=international_code,
    )

  def _rdsy_callback(self, international_code: str, prefix: str) -> str:
    return sms_login._rdsy_callback(self, international_code, prefix)

  def _jsonp_callback(self, prefix: str) -> str:
    return sms_login._jsonp_callback(prefix)

  def _scene_id(self, international_code: str) -> str:
    return sms_login._scene_id(self, international_code)

  def _channel(self, international_code: str) -> str:
    return sms_login._channel(international_code)

  def _find_signed_template(
    self,
    method: str,
    url: str,
    body: str,
  ) -> SignedRequestTemplate | None:
    return har_templates.find_signed_template(self, method, url, body)

  def _resolve_ac_target(
    self,
    family_id: str | int,
    device_id: str | int | None,
  ) -> tuple[str, str]:
    device = self.get_device(family_id, device_id=str(device_id) if device_id else None)
    actual_id = str(device.get("id") or "")
    model_id = str(device.get("model") or device.get("modelId") or "")
    if not actual_id or not model_id:
      raise SuningError("设备信息缺少 id 或 modelId，无法下发控制命令。")
    return actual_id, model_id

  # ------------------------------------------------------------------
  # HAR-backed signed templates
  # ------------------------------------------------------------------

  def load_signed_templates(self) -> None:
    har_templates.load_signed_templates(self)

  def _candidate_har_paths(self) -> list[Path]:
    if not self.har_path:
      return []
    return [self.har_path]

  def _load_signed_templates_from_har(self, har_path: Path) -> None:
    har_templates.load_signed_templates_from_har(self, har_path)

  def _find_signed_template(
    self,
    method: str,
    url: str,
    body: str,
  ) -> SignedRequestTemplate | None:
    return har_templates.find_signed_template(self, method, url, body)

  def _request_with_signed_template(
    self,
    template: SignedRequestTemplate,
    *,
    body: str | None = None,
  ) -> requests.Response:
    return har_templates.request_with_signed_template(self, template, body=body)

  def available_device_template_family_ids(self) -> list[str]:
    return har_templates.available_device_template_family_ids(self)

  # ------------------------------------------------------------------
  # AC control (thin forwards to ac_control)
  # ------------------------------------------------------------------

  def app_oper(
    self,
    device_id: str,
    model_id: str,
    cmd: Mapping[str, Any],
  ) -> dict[str, Any]:
    return ac_control.app_oper(self, device_id, model_id, dict(cmd))

  def turn_on(self, family_id: str | int, device_id: str | int) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.turn_on(self, target_device, model_id)

  def turn_off(self, family_id: str | int, device_id: str | int) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.turn_off(self, target_device, model_id)

  def set_hvac_mode(
    self,
    family_id: str | int,
    device_id: str | int,
    mode: HvacMode,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_hvac_mode(self, target_device, model_id, mode)

  def set_temperature(
    self,
    family_id: str | int,
    device_id: str | int,
    value: float,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_temperature(self, target_device, model_id, value)

  def set_fan_mode(
    self,
    family_id: str | int,
    device_id: str | int,
    speed: FanSpeed,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_fan_mode(self, target_device, model_id, speed)

  def set_swing_mode(
    self,
    family_id: str | int,
    device_id: str | int,
    swing: SwingMode,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_swing_mode(self, target_device, model_id, swing)

  def set_preset_mode(
    self,
    family_id: str | int,
    device_id: str | int,
    preset: PresetMode,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_preset_mode(self, target_device, model_id, preset)

  def set_eco(
    self,
    family_id: str | int,
    device_id: str | int,
    *,
    on: bool,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_eco(self, target_device, model_id, on=on)

  def set_fresh_air(
    self,
    family_id: str | int,
    device_id: str | int,
    *,
    on: bool,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_fresh_air(self, target_device, model_id, on=on)

  def set_aux_heat(
    self,
    family_id: str | int,
    device_id: str | int,
    *,
    on: bool,
  ) -> dict[str, Any]:
    """Toggle electric auxiliary heating.

    Raises :class:`SuningError` when ``on`` is True and the device's
    current ``hvac_mode`` is anything other than ``HEAT`` — the rule
    surfaced by the App is "aux heat only while heating".  When the
    status read fails (``hvac_mode`` is ``None``) we let the call
    through and trust the device to no-op.
    """

    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    current_mode: HvacMode | None = None
    if on:
      try:
        current_mode = self.get_air_conditioner_status(
          family_id,
          device_id=target_device,
        ).hvac_mode
      except SuningError:
        current_mode = None
    return ac_control.set_aux_heat(
      self,
      target_device,
      model_id,
      on=on,
      current_hvac_mode=current_mode,
    )

  def set_vertical_swing(
    self,
    family_id: str | int,
    device_id: str | int,
    *,
    on: bool,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_vertical_swing(self, target_device, model_id, on=on)

  def set_horizontal_swing(
    self,
    family_id: str | int,
    device_id: str | int,
    *,
    on: bool,
  ) -> dict[str, Any]:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.set_horizontal_swing(self, target_device, model_id, on=on)

  def list_device_timers(
    self,
    family_id: str | int,
    device_id: str | int,
  ) -> list[Timer]:
    target_device, _ = self._resolve_ac_target(family_id, device_id)
    return ac_control.list_device_timers(self, target_device)

  def get_device_panel_template(
    self,
    family_id: str | int,
    device_id: str | int,
  ) -> Any:
    target_device, model_id = self._resolve_ac_target(family_id, device_id)
    return ac_control.get_device_panel_template(self, target_device, model_id)


__all__ = [
  "APP_API_GS_SIGN_SECRET",
  "AIR_CONDITIONER_CATEGORY_ID",
  "AIR_CONDITIONER_NAME_KEYWORD",
  "AuthenticationError",
  "CaptchaRequiredError",
  "DEFAULT_APP_ACCEPT_LANGUAGE",
  "DEFAULT_APP_TERMINAL_TYPE",
  "DEFAULT_APP_USER_AGENT",
  "DEFAULT_LOGIN_PAGE_CONFIG",
  "DEFAULT_LOGIN_URL",
  "DEFAULT_TARGET_URL",
  "DEFAULT_TIMEOUT",
  "DEFAULT_USER_AGENT",
  "DEVICE_LIST_URL",
  "FAMILY_LIST_URL",
  "MEMBER_BASE_INFO_URL",
  "MOBILE_SMS_LOGIN_APP_CODE",
  "MOBILE_SMS_LOGIN_APP_VERSION",
  "MOBILE_SMS_LOGIN_CHANNEL",
  "MOBILE_SMS_LOGIN_ORDER_CHANNEL",
  "MOBILE_SMS_LOGIN_REMEMBER_ME_TYPE",
  "MOBILE_SMS_LOGIN_SCENE_ID",
  "MOBILE_SMS_LOGIN_SUB_MODE",
  "MOBILE_SMS_LOGIN_THEME",
  "OPENSH_GET_KEY_URL",
  "SMS_RATE_LIMIT_ERROR_CODE",
  "SERVICE_BOOTSTRAP_URLS",
  "SmsRateLimitedError",
  "SuningError",
  "SuningSmartHomeClient",
  "SUCCESS_RESPONSE_CODES",
  "main",
  "parse_jsonp_or_json",
]
