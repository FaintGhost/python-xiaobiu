"""Smoke test for the xiaobiu.client module re-exports."""

from xiaobiu import SuningSmartHomeClient  # noqa: F401
from xiaobiu import SuningError  # noqa: F401
from xiaobiu.client import main  # noqa: F401


def test_client_module_exposes_suning_smart_home_client() -> None:
  assert SuningSmartHomeClient.__name__ == "SuningSmartHomeClient"


def test_main_is_callable() -> None:
  assert callable(main)
