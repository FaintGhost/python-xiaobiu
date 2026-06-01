"""Cookie serialisation helpers used by the persisted session state."""

from __future__ import annotations

from typing import Any

from requests.cookies import create_cookie

from .models import SerializedCookie


def serialize_cookie(cookie: Any) -> SerializedCookie:
  return SerializedCookie(
    name=cookie.name,
    value=cookie.value,
    domain=cookie.domain,
    path=cookie.path,
    secure=cookie.secure,
    expires=cookie.expires,
    rest=getattr(cookie, "_rest", {}) or {},
  )


def restore_cookie(serialized_cookie: SerializedCookie) -> Any:
  return create_cookie(
    name=serialized_cookie.name,
    value=serialized_cookie.value,
    domain=serialized_cookie.domain,
    path=serialized_cookie.path,
    secure=serialized_cookie.secure,
    expires=serialized_cookie.expires,
    rest=serialized_cookie.rest,
  )


__all__ = ["restore_cookie", "serialize_cookie"]
