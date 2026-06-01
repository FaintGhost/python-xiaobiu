"""HTTP plumbing for the itapig / shcss app-API endpoints.

All module functions take ``client`` by duck type — they only require
``client.session`` and ``client.timeout`` to exist.  Functions never
import :class:`SuningSmartHomeClient` to avoid a circular dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import TYPE_CHECKING, Any, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

from .exceptions import AuthenticationError, SuningError

if TYPE_CHECKING:  # pragma: no cover
  pass

APP_API_GS_SIGN_SECRET = "ad71cef5-c46a-48f7-a810-61f4be3a207a"
DEFAULT_APP_USER_AGENT = "SmartHome/6.4.7 (Android; Android 14; Scale/3.00)"
DEFAULT_APP_TERMINAL_TYPE = "SHCSS_ANDROID"
DEFAULT_APP_ACCEPT_LANGUAGE = (
  "zh-Hans-US;q=1, zh-Hant-US;q=0.9, en-US;q=0.8, ja-US;q=0.7"
)
SUCCESS_RESPONSE_CODES = {"0", "SUCCESS"}


def normalize_url(url: str) -> str:
  parts = urlsplit(url)
  return f"{parts.scheme}://{parts.netloc}{parts.path}"


def canonicalize_request_body(raw_body: str | None, content_type: str | None = None) -> str:
  if not raw_body:
    return ""
  body = raw_body.strip()
  if "json" in (content_type or "").lower():
    try:
      return json.dumps(json.loads(body), separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
      return body
  return body


def build_gs_sign_payload(url_path: str, request_time: int | str, body: str | None) -> str:
  canonical_body = canonicalize_request_body(body, "application/json")
  payload = f"url={url_path}&requestTime={request_time}&data={canonical_body}"
  return payload.replace(" ", "").replace("\n", "").replace("\r", "")


def build_gs_sign(url_path: str, request_time: int | str, body: str | None) -> str:
  payload = build_gs_sign_payload(url_path, request_time, body)
  return hmac.new(
    APP_API_GS_SIGN_SECRET.encode("utf-8"),
    payload.encode("utf-8"),
    hashlib.sha256,
  ).hexdigest()


def build_app_api_headers(url: str, *, body: str, user_agent: str, terminal_type: str) -> dict[str, str]:
  request_time = str(int(_now_ms()))
  trace_id = uuid4().hex
  return {
    "Accept": "*/*",
    "Accept-Language": DEFAULT_APP_ACCEPT_LANGUAGE,
    "Content-Type": "application/json",
    "TerminalVersion": user_agent,
    "User-Agent": user_agent,
    "terminalType": terminal_type,
    "requestTime": request_time,
    "gsSign": build_gs_sign(urlsplit(url).path, request_time, body),
    "snTraceId": trace_id,
    "hiro_trace_id": trace_id,
    "snTraceType": "SDK",
  }


def is_login_redirect(response: Any) -> bool:
  return (
    response.status_code in {301, 302, 303, 307, 308}
    and "passport.suning.com/ids/login" in (response.headers.get("Location", ""))
  )


def request_app_api(
  client: Any,
  url: str,
  *,
  body: str = "",
  bootstrap: callable = None,
) -> Any:
  """Send a signed ``POST`` to ``url`` and re-bootstrap on redirect.

  ``bootstrap`` is an optional callable taking the service name
  (``"shcss"`` or ``"itapig"``); it is called when the first response
  is a login redirect.  Pass ``client.bootstrap_service`` for the
  standard behaviour.
  """

  def send() -> Any:
    return client.session.request(
      "POST",
      url,
      headers=build_app_api_headers(
        url,
        body=body,
        user_agent=client.app_user_agent,
        terminal_type=client.app_terminal_type,
      ),
      data=body,
      timeout=client.timeout,
      allow_redirects=False,
    )

  response = send()
  if is_login_redirect(response):
    if bootstrap is None:
      raise AuthenticationError("app api redirected to login and no bootstrap configured")
    bootstrap("shcss")
    bootstrap("itapig")
    response = send()
  if is_login_redirect(response):
    raise AuthenticationError("itapig service bootstrap failed")
  return response


def decode_app_api_response(response: Any, *, action: str) -> dict[str, Any]:
  response.raise_for_status()
  try:
    data = response.json()
  except ValueError as error:
    raise SuningError(f"{action} 返回了无法解析的 JSON 响应。") from error
  if data.get("responseCode") != "0":
    raise SuningError(data.get("responseMsg") or f"{action} failed")
  return data


# ``time`` imported lazily so app_api stays free of side-effects at
# import time.
def _now_ms() -> float:
  import time

  return time.time() * 1000


__all__ = [
  "APP_API_GS_SIGN_SECRET",
  "DEFAULT_APP_ACCEPT_LANGUAGE",
  "DEFAULT_APP_TERMINAL_TYPE",
  "DEFAULT_APP_USER_AGENT",
  "SUCCESS_RESPONSE_CODES",
  "build_app_api_headers",
  "build_gs_sign",
  "build_gs_sign_payload",
  "canonicalize_request_body",
  "decode_app_api_response",
  "is_login_redirect",
  "normalize_url",
  "request_app_api",
]
