"""Tests for xiaobiu.models new enums and models (Task 001 / BDD Feature 5)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from xiaobiu.models import (
  FanSpeed,
  HvacMode,
  PanelTemplate,
  PresetMode,
  SwingMode,
  Timer,
)


class _HvacHolder(BaseModel):
  mode: HvacMode


class _FanHolder(BaseModel):
  speed: FanSpeed


class _SwingHolder(BaseModel):
  swing: SwingMode


class _PresetHolder(BaseModel):
  preset: PresetMode


def test_hvac_mode_accepts_all_members() -> None:
  for value in ("cool", "heat", "fan_only", "dry", "auto", "off"):
    assert _HvacHolder(mode=value).mode == value


def test_hvac_mode_rejects_unknown() -> None:
  with pytest.raises(ValidationError):
    _HvacHolder(mode="turbo")


def test_fan_speed_accepts_all_members() -> None:
  for value in ("auto", "low", "mid", "high", "higher", "highest"):
    assert _FanHolder(speed=value).speed == value


def test_fan_speed_rejects_unknown() -> None:
  with pytest.raises(ValidationError):
    _FanHolder(speed="medium")


def test_swing_mode_accepts_all_members() -> None:
  for value in ("off", "vertical", "horizontal", "both"):
    assert _SwingHolder(swing=value).swing == value


def test_swing_mode_rejects_unknown() -> None:
  with pytest.raises(ValidationError):
    _SwingHolder(swing="diagonal")


def test_preset_mode_accepts_all_members() -> None:
  for value in ("none", "eco", "fresh_air"):
    assert _PresetHolder(preset=value).preset == value


def test_preset_mode_rejects_unknown() -> None:
  with pytest.raises(ValidationError):
    _PresetHolder(preset="sleep")


def test_panel_template_roundtrip() -> None:
  template = PanelTemplate(
    device_id="dev1",
    model_id="0001000200150000",
    components=["C_POWER", "C_MODE", "C_FANSPEED"],
  )
  assert template.device_id == "dev1"
  assert template.model_id == "0001000200150000"
  assert template.components == ["C_POWER", "C_MODE", "C_FANSPEED"]


def test_panel_template_components_default_empty() -> None:
  template = PanelTemplate(device_id="dev1", model_id="m1")
  assert template.components == []


def test_timer_roundtrip() -> None:
  timer = Timer(
    name="关闭时间",
    schedule="F,00,30,0",
    enabled=False,
    command={"C_POWER": "0"},
  )
  assert timer.name == "关闭时间"
  assert timer.schedule == "F,00,30,0"
  assert timer.enabled is False
  assert timer.command == {"C_POWER": "0"}


def test_timer_command_default_empty() -> None:
  timer = Timer(name="x", schedule="F,00,30,0", enabled=True)
  assert timer.command == {}
