from __future__ import annotations

from .tool_handler_deps import *
from .tool_handler_release_revision_db import (
    inspect_workspace_db_for_revision,
    read_release_file,
)
from .tool_handler_release_revision_plan import classify_release_revision as _classify_revision_plan
from .tool_handler_release_revision_summary import active_release_summary, release_summary
from .tool_handlers_semantic_release import read_active_semantic_release


def read_revision_candidate_release(arguments: dict[str, Any]) -> dict[str, Any]:
    release_path = Path(_required_text(arguments, "release_path")).expanduser().resolve()
    if not release_path.is_file():
        raise ToolFailure(f"release_path ist keine lesbare Datei: {release_path}")
    payload = read_release_file(release_path)
    if not payload:
        raise ToolFailure(f"release_path enthaelt kein lesbares Release-Objekt: {release_path}")
    return {
        "status": "ok",
        "release_path": str(release_path),
        "candidate_release": release_summary(payload),
    }


def inspect_release_revision_context(arguments: dict[str, Any]) -> dict[str, Any]:
    corpus_db_path = Path(_required_text(arguments, "corpus_db_path")).expanduser().resolve()
    db_state = inspect_workspace_db_for_revision(corpus_db_path)
    runtime = _inspect_runtime_for_revision_context(db_state, corpus_db_path)
    return {
        "status": "ok",
        "corpus_db_path": str(corpus_db_path),
        "database_state": db_state,
        "active_release": active_release_summary(runtime["active_release_payload"], runtime["semantic_status"]),
        **runtime,
    }


def classify_release_revision(arguments: dict[str, Any]) -> dict[str, Any]:
    db_state = _required_mapping(arguments, "database_state")
    candidate_summary = _required_mapping(arguments, "candidate_release")
    active_summary = _optional_mapping(arguments, "active_release") or {}
    preflight = _optional_mapping(arguments, "activation_preflight_result")
    preflight_error = _optional_text(arguments, "activation_preflight_error")
    decision = _classify_revision_plan(
        db_state=db_state,
        candidate_summary=candidate_summary,
        active_summary=active_summary,
        preflight=preflight,
        preflight_error=preflight_error or None,
    )
    return {"status": decision["status"], "revision_plan": decision}


def _inspect_runtime_for_revision_context(db_state: dict[str, Any], corpus_db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "semantic_status": None,
        "semantic_status_error": None,
        "active_release_payload": None,
        "active_release_error": None,
    }
    if not db_state["exists"]:
        return result
    result["semantic_status"], result["semantic_status_error"] = _optional_product_call(
        {"action": "semantic_status", "corpus_db_path": str(corpus_db_path)}
    )
    try:
        result["active_release_payload"] = read_active_semantic_release({"corpus_db_path": str(corpus_db_path)})
    except (ContractError, ToolFailure) as exc:
        result["active_release_error"] = str(exc)
    return result


def _optional_product_call(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _invoke_product("corpus_builder", payload), None
    except ContractError as exc:
        return None, str(exc)


__all__ = [name for name in globals() if not name.startswith("__")]
