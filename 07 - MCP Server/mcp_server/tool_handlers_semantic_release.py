from __future__ import annotations

from .tool_handler_deps import *
from .tool_handlers_artifact_rebuild import _corpus_optional_path_action


def read_active_semantic_release(arguments: dict[str, Any]) -> dict[str, Any]:
    return _corpus_optional_path_action("read_active_semantic_release", arguments)


def reset_active_corpus_db(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"action": "reset_active_corpus_db", "confirmation_artifact_path": _required_text(arguments, "confirmation_artifact_path")}
    _add_optional(payload, arguments, "corpus_db_path")
    return _invoke_product("corpus_builder", payload)


def load_semantic_release(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"action": "load_semantic_release", "release_path": _required_text(arguments, "release_path")}
    _add_optional(payload, arguments, "corpus_db_path")
    return _invoke_product("corpus_builder", payload)


def semantic_audit(arguments: dict[str, Any]) -> dict[str, Any]:
    return _corpus_optional_path_action("semantic_audit", arguments)


def activation_preflight(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"action": "activation_preflight", "release_path": _required_text(arguments, "release_path")}
    _add_optional(payload, arguments, "corpus_db_path")
    return _invoke_product("corpus_builder", payload)


def activate_release_on_existing_db(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"action": "activate_semantic_release", "release_path": _required_text(arguments, "release_path")}
    _add_optional(payload, arguments, "corpus_db_path")
    _add_optional(payload, arguments, "confirmation_artifact_path")
    if payload.get("corpus_db_path"):
        payload["write_global_mirrors"] = False
    return _invoke_product("corpus_builder", payload)


def backfill_stale(arguments: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"action": "backfill_stale"}
    _add_optional(payload, arguments, "corpus_db_path")
    if "document_ids" in arguments:
        payload["document_ids"] = _optional_string_list(arguments, "document_ids")
    if "stale_only" in arguments:
        payload["stale_only"] = _optional_bool(arguments, "stale_only", default=True)
    if "limit" in arguments and arguments["limit"] not in (None, ""):
        payload["limit"] = _positive_int(arguments["limit"], "limit")
    return _invoke_product("corpus_builder", payload)


def merge_preflight(arguments: dict[str, Any]) -> dict[str, Any]:
    return _invoke_product("corpus_builder", {
        "action": "merge_preflight",
        "source_db_path": _required_text(arguments, "source_db_path"),
        "target_db_path": _required_text(arguments, "target_db_path"),
    })


def merge_corpora(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "action": "merge_corpus_databases",
        "source_db_path": _required_text(arguments, "source_db_path"),
        "target_db_path": _required_text(arguments, "target_db_path"),
    }
    _add_optional(payload, arguments, "snapshot_risk_confirmation_artifact_path")
    _add_optional(payload, arguments, "collision_resolution_artifact_path")
    return _invoke_product("corpus_builder", payload)


__all__ = [name for name in globals() if not name.startswith("__")]
