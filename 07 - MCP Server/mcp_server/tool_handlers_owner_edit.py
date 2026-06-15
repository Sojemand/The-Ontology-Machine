from __future__ import annotations

from .tool_handler_deps import *
def describe_owner_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(_required_module(arguments), {"action": "describe_surfaces"})


def read_owner_bundle(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(_required_module(arguments), {"action": "read_bundle"})


def read_owner_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(
        _required_module(arguments),
        {"action": "read_surface", "surface_id": _required_text(arguments, "surface_id")},
    )


def validate_owner_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(
        _required_module(arguments),
        {
            "action": "validate_surface",
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )


def write_owner_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(
        _required_module(arguments),
        {
            "action": "write_surface",
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )

__all__ = [name for name in globals() if not name.startswith("__")]
