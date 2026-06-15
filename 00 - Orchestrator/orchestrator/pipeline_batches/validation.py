from __future__ import annotations

import hashlib
import json
import re
from typing import Any


_BATCH_ID_RE = re.compile(r"^pbt_\d{14}_[0-9a-f]{8}_\d+$")


def validate_create_request(payload: dict[str, Any]) -> dict[str, Any]:
    _require_known_fields(
        payload,
        {
            "schema_version",
            "owner_action",
            "workflow_run_id",
            "adapter_call_id",
            "requested_at",
            "pipeline_batch_id",
            "batch_kind",
            "active_database",
            "artifact_root",
            "semantic_release",
            "active_projections",
            "input_files",
            "pending_manifest",
            "target_identity",
            "request_fingerprint",
        },
    )
    _require_request_envelope(payload, "create_pipeline_batch_manifest")
    _require_batch_id(payload)
    return payload


def validate_finalize_request(payload: dict[str, Any]) -> dict[str, Any]:
    _require_known_fields(
        payload,
        {
            "schema_version",
            "owner_action",
            "workflow_run_id",
            "adapter_call_id",
            "requested_at",
            "pipeline_batch_id",
            "pending_manifest_ref",
            "orchestrator_run_ref",
            "corpus_load_refs",
            "output_artifacts",
            "materialized_records",
            "record_counts",
            "correlation_report",
            "final_manifest",
            "target_identity",
            "request_fingerprint",
        },
    )
    _require_request_envelope(payload, "finalize_pipeline_batch_manifest")
    _require_batch_id(payload)
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
    if fingerprint != _request_fingerprint(payload):
        raise ValueError("request_fingerprint does not match payload.")


def _require_batch_id(payload: dict[str, Any]) -> None:
    value = str(payload.get("pipeline_batch_id", "")).strip()
    if not _BATCH_ID_RE.match(value):
        raise ValueError("pipeline_batch_id is invalid.")


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is missing or invalid.")
    return value.strip()


def _request_fingerprint(payload: dict[str, Any]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _require_known_fields(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
