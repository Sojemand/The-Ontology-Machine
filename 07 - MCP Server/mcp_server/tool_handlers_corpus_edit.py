from __future__ import annotations

from typing import Any

from .tool_handler_deps import *


def corpus_builder_describe_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, set(), "corpus_builder.describe_surfaces")
    return _invoke_edit("corpus_builder", {"action": "describe_surfaces"})


def corpus_builder_read_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id"}, "corpus_builder.read_surface")
    return _invoke_edit(
        "corpus_builder",
        {"action": "read_surface", "surface_id": _required_text(arguments, "surface_id")},
    )


def corpus_builder_validate_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "corpus_builder.validate_surface")
    return _invoke_edit(
        "corpus_builder",
        {
            "action": "validate_surface",
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )


def corpus_builder_write_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "corpus_builder.write_surface")
    return _invoke_edit(
        "corpus_builder",
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
