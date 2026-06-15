from __future__ import annotations

from typing import Any

from .tool_handler_deps import *


def validator_describe_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, set(), "validator.describe_surfaces")
    return _invoke_edit("validator", {"action": "describe_surfaces"})


def validator_read_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id"}, "validator.read_surface")
    return _invoke_edit(
        "validator",
        {"action": "read_surface", "surface_id": _required_text(arguments, "surface_id")},
    )


def validator_validate_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "validator.validate_surface")
    return _invoke_edit(
        "validator",
        {
            "action": "validate_surface",
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )


def validator_write_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "validator.write_surface")
    return _invoke_edit(
        "validator",
        {
            "action": "write_surface",
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )


def _reject_unknown(arguments: dict[str, Any], allowed: set[str], tool_name: str) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolFailure(f"{tool_name} kennt diese Argumente nicht: {', '.join(unknown)}")


__all__ = [name for name in globals() if not name.startswith("__")]
