from __future__ import annotations

from .tool_handler_deps import *
def inspect_runtime(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "inspect_runtime")
    return _invoke_admin("orchestrator", {"action": "inspect_runtime"})


def read_runtime_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "read_runtime_settings")
    return _invoke_admin("orchestrator", {"action": "manage_runtime_settings", "operation": "read"})


def write_runtime_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"settings"}, "write_runtime_settings")
    return _invoke_admin(
        "orchestrator",
        {"action": "manage_runtime_settings", "operation": "write", "settings": _required_mapping(arguments, "settings")},
    )


def reset_runtime_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "reset_runtime_settings")
    return _invoke_admin("orchestrator", {"action": "manage_runtime_settings", "operation": "reset"})


def inspect_runtime_credentials(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "inspect_runtime_credentials")
    return _invoke_admin("orchestrator", {"action": "manage_credentials", "operation": "inspect"})


def set_runtime_api_key(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"target", "secret_value"}, "set_runtime_api_key")
    return _invoke_admin(
        "orchestrator",
        {
            "action": "manage_credentials",
            "operation": "set_api_key",
            "target": _required_text(arguments, "target"),
            "secret_value": _required_text(arguments, "secret_value"),
        },
    )


def delete_runtime_api_key(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"target"}, "delete_runtime_api_key")
    return _invoke_admin(
        "orchestrator",
        {"action": "manage_credentials", "operation": "delete_api_key", "target": _required_text(arguments, "target")},
    )


def reveal_secret(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_admin(
        "orchestrator",
        {
            "action": "reveal_secret",
            "target": _required_text(arguments, "target"),
            "purpose": _required_text(arguments, "purpose"),
            "unlock_phrase": _required_text(arguments, "unlock_phrase"),
        },
    )


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")

__all__ = [name for name in globals() if not name.startswith("__")]
