"""Signed-request template cache backed by HAR captures.

The itapig and shcss endpoints require a per-request ``gsSign`` plus a
fresh ``snTraceId``.  When a HAR is provided, we replay the captured
signed headers as a shortcut.  This module owns loading, lookup and
re-execution of those templates.

Functions take ``client`` by duck type — they only need ``client.signed_templates``,
``client.session``, ``client.timeout``.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .app_api import (
  SUCCESS_RESPONSE_CODES,
  canonicalize_request_body,
  is_login_redirect,
  normalize_url,
)
from .parsers import parse_jsonp_or_json
from .models import SignedRequestTemplate

# URL constants — these are intentionally duplicated from the public
# constants exposed by the shcss surface; keeping a private copy here
# avoids a hard import from ``ac_status`` (which itself imports things
# we depend on at module-load time).
_FAMILY_LIST_URL = "https://itapig.suning.com/api/trade/shcss/queryAllFamily"
_DEVICE_LIST_URL = "https://itapig.suning.com/api/trade/shcss/all"
_OPENSH_GET_KEY_URL = "https://opensh.suning.com/shsys-web/cc/api/v3/getKey"

_SUPPORTED_HAR_URLS = {
  normalize_url(_FAMILY_LIST_URL),
  normalize_url(_DEVICE_LIST_URL),
  normalize_url(_OPENSH_GET_KEY_URL),
}


def _decode_har_content(content: dict[str, Any]) -> str:
  text = content.get("text") or ""
  if content.get("encoding") == "base64":
    return base64.b64decode(text).decode("utf-8", "replace")
  return text


def _extract_har_headers(entry: dict[str, Any]) -> dict[str, str]:
  return {
    item["name"]: item["value"]
    for item in entry.get("request", {}).get("headers", [])
    if "name" in item and "value" in item
  }


def _har_response_payload(entry: dict[str, Any]) -> dict[str, Any] | None:
  content = entry.get("response", {}).get("content") or {}
  text = _decode_har_content(content).strip()
  if not text:
    return None
  try:
    return json.loads(text)
  except json.JSONDecodeError:
    return parse_jsonp_or_json(text)


def _har_entry_is_success(entry: dict[str, Any]) -> bool:
  if entry.get("response", {}).get("status") != 200:
    return False
  payload = _har_response_payload(entry)
  if not payload:
    return False
  return str(payload.get("responseCode") or payload.get("code") or "").upper() in SUCCESS_RESPONSE_CODES


def _template_key(method: str, url: str, body: str) -> tuple[str, str, str]:
  return (method.upper(), normalize_url(url), body)


def _candidate_har_paths(client: Any) -> list[Path]:
  if not client.har_path:
    return []
  return [client.har_path]


def load_signed_templates_from_har(client: Any, har_path: Path) -> None:
  if not har_path.exists():
    return
  try:
    payload = json.loads(har_path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return
  entries = payload.get("log", {}).get("entries", [])
  for entry in entries:
    request = entry.get("request", {})
    method = str(request.get("method", "")).upper()
    url = request.get("url", "")
    normalized_url = normalize_url(url)
    if normalized_url not in _SUPPORTED_HAR_URLS or not _har_entry_is_success(entry):
      continue
    headers = _extract_har_headers(entry)
    body = canonicalize_request_body(
      request.get("postData", {}).get("text"),
      headers.get("Content-Type") or headers.get("content-type"),
    )
    template = SignedRequestTemplate(
      method=method,
      url=normalized_url,
      headers=headers,
      body=body,
      har_path=str(har_path),
    )
    client.signed_templates.setdefault(
      _template_key(method, normalized_url, body),
      template,
    )


def load_signed_templates(client: Any) -> None:
  client.signed_templates = {}
  for har_path in _candidate_har_paths(client):
    load_signed_templates_from_har(client, har_path)


def find_signed_template(
  client: Any,
  method: str,
  url: str,
  body: str,
) -> SignedRequestTemplate | None:
  return client.signed_templates.get(_template_key(method, url, body))


def request_with_signed_template(
  client: Any,
  template: SignedRequestTemplate,
  *,
  body: str | None = None,
) -> Any:
  from . import ac_status  # late import to avoid ac_status -> har_templates cycle

  payload = template.body if body is None else body
  request_kwargs: dict[str, Any] = {
    "headers": template.build_headers(),
    "timeout": client.timeout,
    "allow_redirects": False,
  }
  if payload:
    request_kwargs["data"] = payload
  response = client.session.request(
    template.method,
    template.url,
    **request_kwargs,
  )
  if is_login_redirect(response):
    ac_status.query_member_base_info(client)
    response = client.session.request(
      template.method,
      template.url,
      **request_kwargs,
    )
  return response


def available_device_template_family_ids(client: Any) -> list[str]:
  family_ids: set[str] = set()
  for template in client.signed_templates.values():
    if template.method != "POST" or template.url != normalize_url(_DEVICE_LIST_URL):
      continue
    if not template.body:
      continue
    try:
      payload = json.loads(template.body)
    except json.JSONDecodeError:
      continue
    family_id = payload.get("familyId")
    if family_id is not None:
      family_ids.add(str(family_id))
  return sorted(family_ids)


__all__ = [
  "available_device_template_family_ids",
  "find_signed_template",
  "load_signed_templates",
  "load_signed_templates_from_har",
  "request_with_signed_template",
]
