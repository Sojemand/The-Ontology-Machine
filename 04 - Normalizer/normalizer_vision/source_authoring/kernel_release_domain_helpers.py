from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from ..semantic_release.kernel_candidate import stable_hash
from .control_language import control_locale_or_default


def require_owner_envelope(payload: Mapping[str, Any], owner_action: str) -> None:
    if payload.get("schema_version") != "kernel.pipeline_owner_request.v1":
        raise ValueError("schema_version must be kernel.pipeline_owner_request.v1.")
    if payload.get("owner_action") != owner_action:
        raise ValueError(f"owner_action must be {owner_action}.")
    for key in ("workflow_run_id", "adapter_call_id", "requested_at", "request_fingerprint"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string.")
    if not isinstance(payload.get("target_identity"), Mapping):
        raise ValueError("target_identity must be an object.")
    if str(payload.get("request_fingerprint") or "") != request_fingerprint(payload):
        raise ValueError("request_fingerprint does not match payload.")


def request_fingerprint(payload: Mapping[str, Any]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def owner_ok(
    owner_action: str,
    capability: str,
    target_identity: Mapping[str, Any],
    output_refs: Mapping[str, Any],
    *,
    diagnostics: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "value": {
            "schema_version": "kernel.pipeline_owner_result.v1",
            "owner_module": "04 - Normalizer",
            "owner_action": owner_action,
            "capability": capability,
            "status": "ok",
            "target_identity": dict(target_identity),
            "artifact_refs": dict(output_refs),
            "receipt_fields": receipt_fields(owner_action, target_identity, output_refs),
            "diagnostics": list(diagnostics or ()),
            "warnings": list(warnings or ()),
            **dict(output_refs),
        },
        "output_refs": dict(output_refs),
        "target_identity_proof": {
            key: value
            for key, value in dict(target_identity).items()
            if key.endswith("_hash") or key in {"release_fingerprint", "merge_run_id", "pipeline_batch_id"}
        },
        "receipt_fields": receipt_fields(owner_action, target_identity, output_refs),
        "diagnostics": list(diagnostics or ()),
        "warnings": list(warnings or ()),
    }


def receipt_fields(owner_action: str, target_identity: Mapping[str, Any], output_refs: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {"owner_module": "04 - Normalizer", "owner_action": owner_action}
    for key in (
        "artifact_root_path_hash",
        "database_path_hash",
        "release_fingerprint",
        "merge_run_id",
        "pipeline_batch_id",
    ):
        if target_identity.get(key):
            receipt[key] = target_identity[key]
    for key in ("taxonomy_fingerprint", "projection_set_fingerprint", "semantic_release_id", "semantic_release_version"):
        if output_refs.get(key):
            receipt[key] = output_refs[key]
    release_ref = output_refs.get("release_ref")
    if isinstance(release_ref, Mapping):
        for key in ("release_id", "release_version", "release_fingerprint"):
            if release_ref.get(key):
                receipt[key] = release_ref[key]
    return receipt


def mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def nested_mapping(payload: Mapping[str, Any], key: str, child_key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        child = value.get(child_key)
        if isinstance(child, Mapping):
            return dict(child)
    return {}


def projection_component_identity(
    projection_refs: list[Mapping[str, Any]],
    projection_set_fingerprint: str,
) -> dict[str, Any]:
    if len(projection_refs) == 1:
        return dict(projection_refs[0])
    if not projection_refs:
        return {}
    return {
        "projection_ids": [str(item.get("projection_id")) for item in projection_refs if item.get("projection_id")],
        "projection_refs": [dict(item) for item in projection_refs],
        "projection_set_fingerprint": projection_set_fingerprint,
    }


def projection_refs_from_identity(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Mapping):
        return []
    if isinstance(value.get("projection_refs"), list):
        return [dict(item) for item in value["projection_refs"] if isinstance(item, Mapping)]
    component = value.get("component_identity")
    if isinstance(component, Mapping):
        return projection_refs_from_identity(component)
    if value.get("projection_id") or value.get("projection_ids"):
        return [dict(value)]
    return []


def updated_release_ref(
    base_release_ref: Mapping[str, Any],
    *,
    taxonomy_ref: Mapping[str, Any] | None = None,
    projection_refs: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    updated = dict(base_release_ref)
    if taxonomy_ref is not None:
        updated["taxonomy_ref"] = dict(taxonomy_ref)
    if projection_refs is not None:
        updated["projection_refs"] = [dict(item) for item in projection_refs]
    updated["release_fingerprint"] = stable_hash(repr(sorted(updated.items())))
    updated.setdefault("release_id", f"updated_{updated['release_fingerprint'][:12]}")
    updated.setdefault("release_version", "updated.v1")
    updated.setdefault("runtime_locale", control_locale_or_default(updated.get("taxonomy_ref", {}).get("runtime_locale")))
    return updated
