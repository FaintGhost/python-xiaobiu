"""Domain exceptions raised across the xiaobiu client surface.

Leaf module — no internal dependencies so any other module can import
from here without creating a cycle.
"""

from __future__ import annotations


class SuningError(RuntimeError):
  """Base error for all Suning client failures."""


class CaptchaRequiredError(SuningError):
  """SMS send refused until a captcha token is supplied."""

  def __init__(self, risk_type: str, message: str, sms_ticket: str | None = None) -> None:
    super().__init__(message)
    self.risk_type = risk_type
    self.sms_ticket = sms_ticket


class SmsRateLimitedError(SuningError):
  """SMS dispatch rate limit hit (suning error code 00201)."""

  def __init__(self, message: str, *, error_code: str = "00201") -> None:
    super().__init__(message)
    self.error_code = error_code


class AuthenticationError(SuningError):
  """Session is gone or login response was invalid."""


__all__ = [
  "AuthenticationError",
  "CaptchaRequiredError",
  "SmsRateLimitedError",
  "SuningError",
]
