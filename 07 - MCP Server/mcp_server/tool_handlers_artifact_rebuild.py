from __future__ import annotations

from .tool_handler_deps import *
def _corpus_optional_path_action(action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"action": action}
    _add_optional(payload, arguments, "corpus_db_path")
    return _invoke_product("corpus_builder", payload)


def _artifact_action(action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_product("corpus_builder", _artifact_payload(action, arguments))


def _artifact_payload(action: str, arguments: dict[str, Any], *, include_corpus_db: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": action}
    for key in ("pipeline_root", "normalized_dir", "structured_dir", "validation_dir", "raw_dir"):
        _add_optional(payload, arguments, key)
    if include_corpus_db:
        _add_optional(payload, arguments, "corpus_db_path")
    return payload


def preview_rebuild_from_artifacts(arguments: dict[str, Any]) -> dict[str, Any]:
    return _artifact_action("preview_rebuild_from_artifacts", arguments)


def rebuild_corpus_from_artifacts(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = _artifact_payload("rebuild_from_artifacts", arguments)
    if "replace_existing" in arguments:
        payload["replace_existing"] = _optional_bool(arguments, "replace_existing", default=True)
    return _invoke_product("corpus_builder", payload)

__all__ = [name for name in globals() if not name.startswith("__")]
