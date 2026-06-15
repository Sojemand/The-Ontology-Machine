from __future__ import annotations

from .tool_handler_deps import *


def orchestrator_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "orchestrator.healthcheck")
    return _invoke_product("orchestrator", {"action": "healthcheck"})


def orchestrator_reset(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "orchestrator.reset")
    ui_state = _read_active_orchestrator_ui_state()
    return _invoke_product("orchestrator", {"action": "reset", "ui_state": ui_state})


__all__ = [name for name in globals() if not name.startswith("__")]
