from __future__ import annotations

from .tool_handler_deps import *
def list_default_blueprints(_arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(_arguments, "list_default_blueprints")
    result = _invoke_product("normalizer", {"action": "list_default_blueprints"})
    if str(result.get("status") or "").casefold() == "ok":
        result = {**result, "status": "ok"}
    return result

def inspect_source_document_sample(arguments: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": "inspect_source_document_sample",
        "source_document_path": _required_text(arguments, "source_document_path"),
    }
    for key in ("sample_label",):
        _add_optional(payload, arguments, key)
    for key in ("max_excerpt_chars", "timeout_seconds", "cleanup_days"):
        if key in arguments and arguments[key] not in (None, ""):
            payload[key] = _positive_or_zero_int(arguments[key], key) if key == "cleanup_days" else _positive_int(arguments[key], key)
    return _invoke_product("orchestrator", payload)


def export_default_blueprint_release(arguments: dict[str, Any]) -> dict[str, Any]:
    output_path = _required_text(arguments, "output_path")
    _validate_release_output_path(output_path)
    payload = {
        "action": "export_default_blueprint_release",
        "blueprint_ref": _optional_text(arguments, "blueprint_ref") or "default",
        "target_locale": _optional_text(arguments, "target_locale"),
        "output_path": output_path,
    }
    return _invoke_product("normalizer", payload)

__all__ = [name for name in globals() if not name.startswith("__")]
