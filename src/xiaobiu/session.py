"""Session renewal that mirrors the app's silent login.

``AutoLoginPresenter.autoLogin`` posts the passport login form with no
credentials at all: the existing cookies are what identifies the user, and
the ``service`` parameter decides which site's ticket passport mints.  A
successful call answers ``ok`` and redirects to ``<service>?ticket=ST...``;
an expired session answers the login-page JSON instead.
"""

from __future__ import annotations

from typing import Any

from .exceptions import AuthenticationError, SuningError

SILENT_LOGIN_URL = "https://passport.suning.com/ids/login"
SILENT_LOGIN_SERVICE = "https://shcss.suning.com/shcss-web/"
SILENT_LOGIN_THEME = "zn"
SILENT_LOGIN_CHANNEL = "MOBILE"
SILENT_LOGIN_REMEMBER_ME_TYPE = "app"


def build_silent_login_payload(client: Any) -> dict[str, str]:
  """Form fields ``autoLogin`` sends; credentials are deliberately absent."""

  return {
    "rememberMe": "true",
    "rememberMeType": SILENT_LOGIN_REMEMBER_ME_TYPE,
    "service": SILENT_LOGIN_SERVICE,
    "dfpToken": str(getattr(client.state, "dfp_token", "") or ""),
    "loginTheme": SILENT_LOGIN_THEME,
    "loginChannel": SILENT_LOGIN_CHANNEL,
    "terminal": SILENT_LOGIN_CHANNEL,
    "jsonViewType": "true",
  }


def silent_login(client: Any) -> dict[str, Any]:
  """Renew the session with the cookies already in the session jar."""

  response = client.session.post(
    SILENT_LOGIN_URL,
    data=build_silent_login_payload(client),
    timeout=client.timeout,
    allow_redirects=True,
  )
  body = (response.text or "").strip()
  ticket = "ticket=ST" in str(response.url)
  if ticket or body.lower() == "ok":
    client._touch_state()
    return {
      "renewed": True,
      "final_url": response.url,
      "body": body[:120],
    }
  if "loginPage" in body or '"res_code":-1' in body:
    raise AuthenticationError("静默登录失败：会话已失效，请重新登录")
  raise SuningError(f"静默登录返回了无法识别的响应: {body[:120]}")


__all__ = [
  "SILENT_LOGIN_CHANNEL",
  "SILENT_LOGIN_SERVICE",
  "SILENT_LOGIN_URL",
  "build_silent_login_payload",
  "silent_login",
]
