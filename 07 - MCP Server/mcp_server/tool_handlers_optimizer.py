from __future__ import annotations

from typing import Any

from .tool_handler_deps import *
from .tool_handlers_optimizer_helpers import *

_CLASSIFY_KEYS = {"source_path", "input_root", "timeout_seconds"}
_EXTRACT_KEYS = {
    "source_path",
    "input_root",
    "output_root",
    "raw_output_path",
    "page_images_dir",
    "logical_source_path",
    "optimizer_profile",
    "runtime_policy_path",
    "timeout_seconds",
}
_HEALTHCHECK_KEYS = {"optimizer_profile", "scope", "required_dependencies", "timeout_seconds"}
_SCAN_KEYS = {"input_root", "debug_root", "session_root", "optimizer_profile", "filters", "hash_tools", "timeout_seconds"}


def optimizer_classify_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _CLASSIFY_KEYS, "optimizer.classify_document")
    input_root = _existing_dir(arguments, "input_root")
    source_path = _existing_file(arguments, "source_path", root=input_root)
    return _invoke_optimizer({"action": "classify_document", "source_path": str(source_path), "input_root": str(input_root)}, arguments)


def optimizer_extract_document(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _EXTRACT_KEYS, "optimizer.extract_document")
    input_root = _existing_dir(arguments, "input_root")
    output_root = _existing_dir(arguments, "output_root")
    source_path = _existing_file(arguments, "source_path", root=input_root)
    raw_output_path = _output_path(arguments, "raw_output_path", root=output_root)
    page_images_dir = _output_path(arguments, "page_images_dir", root=output_root)
    profile = _optimizer_profile(arguments, required=True)
    payload: dict[str, Any] = {
        "action": "extract_document",
        "source_path": str(source_path),
        "input_root": str(input_root),
        "output_root": str(output_root),
        "raw_output_path": str(raw_output_path),
        "page_images_dir": str(page_images_dir),
        "logical_source_path": _relative_logical_path(arguments),
        "optimizer_profile": profile,
    }
    runtime_policy_path = _runtime_policy_path(arguments, required=profile == "vision")
    if runtime_policy_path is not None:
        payload["runtime_policy_path"] = str(runtime_policy_path)
    return _invoke_optimizer(payload, arguments)


def optimizer_healthcheck(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _HEALTHCHECK_KEYS, "optimizer.healthcheck")
    payload: dict[str, Any] = {"action": "healthcheck"}
    profile = _optimizer_profile(arguments, required=False)
    if profile:
        payload["optimizer_profile"] = profile
    scope = _optional_text(arguments, "scope")
    if scope:
        payload["scope"] = scope
    dependencies = _healthcheck_dependencies(arguments)
    if dependencies:
        payload["required_dependencies"] = dependencies
    return _invoke_optimizer(payload, arguments)


def optimizer_scan_debug_input(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, _SCAN_KEYS, "optimizer.scan_debug_input")
    input_root = _existing_dir(arguments, "input_root")
    debug_root = _existing_dir(arguments, "debug_root")
    payload: dict[str, Any] = {
        "action": "scan_debug_input",
        "input_root": str(input_root),
        "session_root": str(_session_root(arguments, debug_root)),
        "mode": "scan",
    }
    _add_if_present(payload, "optimizer_profile", _optimizer_profile(arguments, required=False))
    _add_if_present(payload, "filters", _filters(arguments))
    _add_if_present(payload, "hash_tools", _hash_tools(arguments))
    return _invoke_optimizer(payload, arguments)


def optimizer_describe_surfaces(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, set(), "optimizer.describe_surfaces")
    return _invoke_edit("optimizer", {"action": "describe_surfaces"})


def optimizer_read_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id"}, "optimizer.read_surface")
    return _invoke_edit("optimizer", {"action": "read_surface", "surface_id": _required_text(arguments, "surface_id")})


def optimizer_validate_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "optimizer.validate_surface")
    return _optimizer_surface_action("validate_surface", arguments)


def optimizer_write_surface(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(arguments, {"surface_id", "value"}, "optimizer.write_surface")
    return _optimizer_surface_action("write_surface", arguments)


def _optimizer_surface_action(action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_edit(
        "optimizer",
        {
            "action": action,
            "surface_id": _required_text(arguments, "surface_id"),
            "value": _required_mapping(arguments, "value"),
        },
    )


def _add_if_present(payload: dict[str, Any], key: str, value: Any) -> None:
    if value:
        payload[key] = value


def _invoke_optimizer(payload: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    timeout = _timeout_seconds(arguments)
    if timeout is None:
        return _invoke_product("optimizer", payload)
    return _invoke_product("optimizer", payload, timeout=timeout)


__all__ = [name for name in globals() if not name.startswith("__")]
