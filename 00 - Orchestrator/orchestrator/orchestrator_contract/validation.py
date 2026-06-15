"""Hard validation for orchestrator contract payloads."""

from __future__ import annotations

from typing import Any

from .types import (
    ACTIVATE_CORPUS_CONTEXT_ACTION,
    ActionName,
    CREATE_ARTIFACT_TREE_ACTION,
    CREATE_PIPELINE_BATCH_MANIFEST_ACTION,
    EMBEDDINGS_ACTION,
    FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION,
    HEALTHCHECK_ACTION,
    INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION,
    KERNEL_LLM_GENERATE_ACTION,
    KERNEL_LLM_RUNTIME_PROFILE_ACTION,
    RESET_ACTION,
    RESET_PIPELINE_LOGS_ACTION,
    RUN_ACTION,
    VALIDATE_ARTIFACT_TREE_ACTION,
)


def require_action(payload: dict[str, Any]) -> ActionName:
    body = request_body(payload)
    value = body.get("action", body.get("owner_action"))
    if not isinstance(value, str):
        raise ValueError("action is missing or invalid.")
    action = value.strip()
    if action == RUN_ACTION:
        return RUN_ACTION
    if action == RESET_ACTION:
        return RESET_ACTION
    if action == RESET_PIPELINE_LOGS_ACTION:
        return RESET_PIPELINE_LOGS_ACTION
    if action == EMBEDDINGS_ACTION:
        return EMBEDDINGS_ACTION
    if action == ACTIVATE_CORPUS_CONTEXT_ACTION:
        return ACTIVATE_CORPUS_CONTEXT_ACTION
    if action == INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION:
        return INSPECT_SOURCE_DOCUMENT_SAMPLE_ACTION
    if action == KERNEL_LLM_RUNTIME_PROFILE_ACTION:
        return KERNEL_LLM_RUNTIME_PROFILE_ACTION
    if action == KERNEL_LLM_GENERATE_ACTION:
        return KERNEL_LLM_GENERATE_ACTION
    if action == HEALTHCHECK_ACTION:
        return HEALTHCHECK_ACTION
    if action == CREATE_ARTIFACT_TREE_ACTION:
        return CREATE_ARTIFACT_TREE_ACTION
    if action == VALIDATE_ARTIFACT_TREE_ACTION:
        return VALIDATE_ARTIFACT_TREE_ACTION
    if action == CREATE_PIPELINE_BATCH_MANIFEST_ACTION:
        return CREATE_PIPELINE_BATCH_MANIFEST_ACTION
    if action == FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION:
        return FINALIZE_PIPELINE_BATCH_MANIFEST_ACTION
    raise ValueError(f"Unknown action: {action}")


def request_body(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") == "adapter.call_request.v1":
        inner = payload.get("request_payload")
        if isinstance(inner, dict):
            return inner
    return payload


def ui_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("ui_state", {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("ui_state must be a JSON object.")
    return value


def optional_snapshot_path(payload: dict[str, Any]) -> str:
    value = payload.get("snapshot_path")
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError("snapshot_path must be a string.")
    return value.strip()


def activate_corpus_context_payload(payload: dict[str, Any]) -> dict[str, str]:
    allowed = {"action", "corpus_db_path", "corpus_output_folder", "artifact_folder", "input_folder"}
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
    corpus_db_path = _optional_text(payload.get("corpus_db_path"))
    if not corpus_db_path:
        raise ValueError("corpus_db_path is missing or invalid.")
    result = {"corpus_db_path": corpus_db_path}
    corpus_output_folder = _optional_text(payload.get("corpus_output_folder"))
    if corpus_output_folder:
        result["corpus_output_folder"] = corpus_output_folder
    artifact_folder = _optional_text(payload.get("artifact_folder"))
    if artifact_folder:
        result["artifact_folder"] = artifact_folder
    input_folder = _optional_text(payload.get("input_folder"))
    if input_folder:
        result["input_folder"] = input_folder
    return result


def inspect_source_document_sample_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "action",
        "source_document_path",
        "max_excerpt_chars",
        "timeout_seconds",
        "cleanup_days",
        "sample_label",
    }
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
    source_document_path = _optional_text(payload.get("source_document_path"))
    if not source_document_path:
        raise ValueError("source_document_path is missing or invalid.")
    result: dict[str, Any] = {"source_document_path": source_document_path}
    max_excerpt_chars = _optional_positive_int(payload.get("max_excerpt_chars"), field="max_excerpt_chars")
    if max_excerpt_chars is not None:
        result["max_excerpt_chars"] = max_excerpt_chars
    timeout_seconds = _optional_positive_int(payload.get("timeout_seconds"), field="timeout_seconds")
    if timeout_seconds is not None:
        result["timeout_seconds"] = timeout_seconds
    cleanup_days = _optional_non_negative_int(payload.get("cleanup_days"), field="cleanup_days")
    if cleanup_days is not None:
        result["cleanup_days"] = cleanup_days
    sample_label = _optional_text(payload.get("sample_label"))
    if sample_label:
        result["sample_label"] = sample_label
    return result


def kernel_llm_generate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"action", "llm_provider_request"}
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
    request = payload.get("llm_provider_request")
    if not isinstance(request, dict):
        raise ValueError("llm_provider_request is missing or invalid.")
    return {"llm_provider_request": dict(request)}


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Path values must be strings.")
    return value.strip()


def _optional_positive_int(value: Any, *, field: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a positive integer.") from None
    if parsed < 1:
        raise ValueError(f"{field} must be a positive integer.")
    return parsed


def _optional_non_negative_int(value: Any, *, field: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a non-negative integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a non-negative integer.") from None
    if parsed < 0:
        raise ValueError(f"{field} must be a non-negative integer.")
    return parsed
