"""Pure parsing helpers for Suning HTTP payloads.

- ``parse_jsonp_or_json`` accepts both flavours Suning returns (raw
  ``{...}`` and ``callback({...})``).
- ``parse_login_page_config`` extracts RSA keys / step flags from the
  passport login page HTML.
- ``extract_risk_context_script_urls`` pulls the fingerprinting scripts
  that the in-page captcha bridge depends on.
- ``_extract_business_error_code`` normalises the 5-digit error code
  Suning sometimes hides inside a longer message.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

from .exceptions import SuningError
from .models import LoginPageConfig


def parse_jsonp_or_json(payload: str) -> dict[str, Any]:
  text = payload.strip()
  if not text:
    raise SuningError("empty response")
  if text[0] == "{":
    return json.loads(text)
  match = re.match(r"^[^(]+\((.*)\)\s*;?\s*$", text, re.S)
  if not match:
    raise SuningError(f"unable to parse jsonp payload: {text[:120]!r}")
  return json.loads(match.group(1))


def _extract_business_error_code(*values: Any) -> str | None:
  for value in values:
    if value is None:
      continue
    text = str(value).strip()
    if not text:
      continue
    if re.fullmatch(r"\d{5}", text):
      return text
    match = re.search(r"\((\d{5})\)\s*$", text)
    if match:
      return match.group(1)
  return None


def parse_login_page_config(html_text: str) -> LoginPageConfig:
  def extract(pattern: str, name: str) -> str:
    match = re.search(pattern, html_text, re.S)
    if not match:
      raise SuningError(f"missing {name} in login page")
    return match.group(1)

  return LoginPageConfig(
    login_pbk=extract(r'var\s+loginPBK="([^"]+)"', "loginPBK"),
    rdsy_key=extract(r'var\s+rdsyKey="([^"]+)"', "rdsyKey"),
    rdsy_app_code=extract(r'rdsyAppCode:"([^"]+)"', "rdsyAppCode"),
    step_flag=extract(r'stepFlag:"([^"]+)"', "stepFlag"),
    step_two_flag=extract(r'stepTwoFlag:"([^"]+)"', "stepTwoFlag"),
    step_three_flag=extract(r'stepThreeFlag:"([^"]+)"', "stepThreeFlag"),
    rdsy_scene_id=extract(r'rdsySceneId:"([^"]+)"', "rdsySceneId"),
    rdsy_scene_id_yghk=extract(r'rdsySceneIdYGHK:"([^"]+)"', "rdsySceneIdYGHK"),
    channel=extract(r'channel:"([^"]+)"', "channel"),
    check_account_key=extract(r'checkAccountKey:\s*"([^"]+)"', "checkAccountKey"),
  )


def extract_risk_context_script_urls(html_text: str) -> list[str]:
  patterns = [
    r'<script[^>]+src="(https://mmds\.suning\.com/mmds/mmds\.js[^"]+)"',
    r'<script[^>]+src="(https://oss\.suning\.com/mmds/mmds/js/[^"]+\.js)"',
    r'<script[^>]+src="(https://dfp\.suning\.com/dfprs-collect/dist/fp\.js[^"]+)"',
  ]
  urls: list[str] = []
  for pattern in patterns:
    match = re.search(pattern, html_text, re.I)
    if not match:
      continue
    url = html.unescape(match.group(1))
    if url not in urls:
      urls.append(url)
  return urls


__all__ = [
  "_extract_business_error_code",
  "extract_risk_context_script_urls",
  "parse_jsonp_or_json",
  "parse_login_page_config",
]
