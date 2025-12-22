import os

from backend.app.core.engine_registry.kill_switch import is_engine_enabled


def test_engine_kill_switch_disabled_by_default() -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    assert is_engine_enabled("engine.dummy") is False

