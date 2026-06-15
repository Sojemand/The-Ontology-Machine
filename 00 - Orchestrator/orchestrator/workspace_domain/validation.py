from __future__ import annotations

import hashlib
import json
from typing import Any

from .types import KERNEL_ARTIFACT_TREE_VERSION


def validate_create_request(payload: dict[str, Any]) -> dict[str, Any]:
    _require_known_fields(
        payload,
        {
            "schema_version",
            "owner_action",
            "workflow_run_id",
            "adapter_call_id",
            "requested_at",
            "artifact_root_parent",
            "artifact_root_name",
            "create_mode",
            "folder_contract_version",
            "target_identity",
            "allow_existing_empty_root",
            "expected_artifact_root_path_hash",
            "dry_run",
            "request_fingerprint",
        },
    )
    _require_request_envelope(payload, "create_artifact_tree")
    if payload.get("folder_contract_version") != KERNEL_ARTIFACT_TREE_VERSION:
        raise ValueError(f"folder_contract_version must be {KERNEL_ARTIFACT_TREE_VERSION}.")
    create_mode = _required_text(payload, "create_mode")
    if create_mode not in {"create_new", "idempotent_create", "validate_existing_then_create_missing"}:
        raise ValueError("create_mode is invalid.")
    return payload


def validate_check_request(payload: dict[str, Any]) -> dict[str, Any]:
    _require_known_fields(
        payload,
        {
            "schema_version",
            "owner_action",
            "workflow_run_id",
            "adapter_call_id",
            "requested_at",
            "artifact_root_path",
            "folder_contract_version",
            "target_identity",
            "require_empty_input",
            "require_semantic_release_folder",
            "require_corpus_folder",
            "return_unexpected_paths",
            "request_fingerprint",
        },
    )
    _require_request_envelope(payload, "validate_artifact_tree")
    if payload.get("folder_contract_version") != KERNEL_ARTIFACT_TREE_VERSION:
        raise ValueError(f"folder_contract_version must be {KERNEL_ARTIFACT_TREE_VERSION}.")
    _required_text(payload, "artifact_root_path")
    return payload


def _require_request_envelope(payload: dict[str, Any], owner_action: str) -> None:
    if payload.get("schema_version") != "kernel.pipeline_owner_request.v1":
        raise ValueError("schema_version must be kernel.pipeline_owner_request.v1.")
    if payload.get("owner_action") != owner_action:
        raise ValueError(f"owner_action must be {owner_action}.")
    _required_text(payload, "workflow_run_id")
    _required_text(payload, "adapter_call_id")
    _required_text(payload, "requested_at")
    if not isinstance(payload.get("target_identity"), dict):
        raise ValueError("target_identity must be an object.")
    fingerprint = _required_text(payload, "request_fingerprint")
    if fingerprint != request_fingerprint(payload):
        raise ValueError("request_fingerprint does not match payload.")


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is missing or invalid.")
    return value.strip()


def request_fingerprint(payload: dict[str, Any]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


_request_fingerprint = request_fingerprint


def _require_known_fields(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
