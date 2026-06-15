from __future__ import annotations

from typing import Any, Mapping

from ..semantic_release.kernel_candidate import compile_candidate, stable_hash
from ..semantic_release.kernel_merge import merge_candidates
from .control_language import control_locale_or_default
from .kernel_release_artifacts import materialize_custom_projection_artifact, materialize_custom_taxonomy_artifact
from .kernel_release_domain_helpers import (
    mapping as _mapping,
    nested_mapping as _nested_mapping,
    owner_ok as _owner_ok,
    projection_refs_from_identity as _projection_refs_from_identity,
    require_owner_envelope,
    updated_release_ref as _updated_release_ref,
)
from .kernel_release_materialization import materialize_candidate_release
from .kernel_projection_validation import validate_projection_binding_payload
from .kernel_update_state_mapping import extract_update_state, projection_identity, taxonomy_identity


def dispatch_kernel_owner_action(action: str, payload: dict[str, Any], *, project_root) -> dict[str, Any]:
    require_owner_envelope(payload, action)
    actions = {
        "materialize_custom_taxonomy_artifact": lambda: materialize_custom_taxonomy_artifact(payload),
        "materialize_custom_projection_artifact": lambda: materialize_custom_projection_artifact(payload),
        "apply_taxonomy_update_state": lambda: apply_taxonomy_update_state(payload),
        "apply_projection_update_state": lambda: apply_projection_update_state(payload),
        "remove_taxonomy_from_release": lambda: remove_taxonomy_from_release(payload),
        "remove_projection_from_release": lambda: remove_projection_from_release(payload),
        "validate_projection_binding": lambda: validate_projection_binding(payload),
        "compile_semantic_release_candidate": lambda: compile_semantic_release_candidate(payload),
        "materialize_semantic_release_candidate": lambda: materialize_semantic_release_candidate(payload),
        "merge_semantic_release_candidates": lambda: merge_semantic_release_candidates(payload),
    }
    return actions[action]()


def apply_taxonomy_update_state(payload: dict[str, Any]) -> dict[str, Any]:
    update_state = extract_update_state(payload, "update_state_payload", "update_state")
    target_identity = _mapping(payload, "target_identity")
    base_release_ref = _mapping(payload, "base_release_ref")
    identity = taxonomy_identity(update_state)
    release_ref = _updated_release_ref(base_release_ref, taxonomy_ref=identity)
    output = {
        "updated_taxonomy_ref": identity,
        "updated_release_component_ref": {"taxonomy_ref": identity},
        "component_fingerprint": identity["taxonomy_fingerprint"],
        "change_summary": {"operation_mode": payload.get("operation_mode", "additive")},
        "work_package_ref": {"updated_release_ref": release_ref},
        "work_package_fingerprint": stable_hash(repr(sorted(release_ref.items()))),
        "validation_status": "created",
    }
    return _owner_ok("apply_taxonomy_update_state", "semantic_release_domain_service", target_identity, output)


def apply_projection_update_state(payload: dict[str, Any]) -> dict[str, Any]:
    update_state = extract_update_state(payload, "update_state_payload", "update_state")
    target_identity = _mapping(payload, "target_identity")
    taxonomy_ref = _mapping(payload, "taxonomy_ref")
    identity = projection_identity(update_state, taxonomy_ref=taxonomy_ref)
    projection_refs = [
        {
            "projection_id": projection_id,
            "projection_fingerprint": identity["projection_fingerprints"][projection_id],
            "included_taxonomy_codes": list(identity["included_taxonomy_codes"]),
        }
        for projection_id in identity["projection_ids"]
    ]
    base_release_ref = _mapping(payload, "base_release_ref")
    release_ref = _updated_release_ref(base_release_ref, projection_refs=projection_refs)
    output = {
        "updated_projection_refs": projection_refs,
        "projection_set_fingerprint": stable_hash(repr(projection_refs)),
        "validation_required": True,
        "change_summary": {"operation_mode": payload.get("operation_mode", "additive")},
        "work_package_ref": {"updated_release_ref": release_ref},
        "work_package_fingerprint": stable_hash(repr(sorted(release_ref.items()))),
        "validation_status": "created",
    }
    return _owner_ok("apply_projection_update_state", "semantic_release_domain_service", target_identity, output)


def remove_taxonomy_from_release(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    release_ref = _mapping(payload, "release_ref")
    updated = dict(release_ref)
    updated["taxonomy_ref"] = {}
    output = {
        "updated_release_ref": updated,
        "removed_component_refs": list(payload.get("taxonomy_component_refs", [])),
        "completeness_state": "incomplete",
        "affected_projection_refs": list(release_ref.get("projection_refs", [])),
    }
    return _owner_ok("remove_taxonomy_from_release", "semantic_release_domain_service", target_identity, output)


def remove_projection_from_release(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    release_ref = _mapping(payload, "release_ref")
    removed_ids = set(str(item) for item in payload.get("projection_ids", ()))
    projection_refs = [dict(item) for item in release_ref.get("projection_refs", []) if isinstance(item, Mapping)]
    remaining = [item for item in projection_refs if str(item.get("projection_id", "")) not in removed_ids]
    updated = dict(release_ref)
    updated["projection_refs"] = remaining
    completeness = "complete" if remaining else "incomplete"
    output = {
        "updated_release_ref": updated,
        "removed_projection_refs": [item for item in projection_refs if str(item.get("projection_id", "")) in removed_ids],
        "remaining_projection_refs": remaining,
        "completeness_state": completeness,
    }
    return _owner_ok("remove_projection_from_release", "semantic_release_domain_service", target_identity, output)


def validate_projection_binding(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    taxonomy_ref = _mapping(payload, "taxonomy_ref")
    projection_refs = [dict(item) for item in payload.get("projection_refs", payload.get("projection_artifact_refs", ())) if isinstance(item, Mapping)]
    if not projection_refs:
        projection_refs = _projection_refs_from_identity(payload.get("custom_projection"))
    ok, errors, warnings = validate_projection_binding_payload(taxonomy_ref=taxonomy_ref, projection_refs=projection_refs)
    output = {
        "is_valid": ok,
        "projection_binding_report_ref": {"artifact_path": "validation/projection_binding_report.json"},
        "projection_set_fingerprint": stable_hash(repr(projection_refs)),
        "errors": errors,
        "warnings": warnings,
        "validation_status": "validated" if ok else "invalid",
        "summary": "" if ok else "Projection references unknown taxonomy codes.",
    }
    return _owner_ok("validate_projection_binding", "semantic_release_domain_service", target_identity, output, diagnostics=[{"code": item} for item in errors], warnings=[{"code": item} for item in warnings])


def compile_semantic_release_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    taxonomy_ref = _mapping(payload, "taxonomy_ref") or _nested_mapping(payload, "staged_taxonomy_ref", "component_identity")
    projection_refs = payload.get("projection_refs")
    if not isinstance(projection_refs, list):
        projection_refs = []
    if not projection_refs:
        staged_projection = _mapping(payload, "staged_projection_ref")
        if staged_projection:
            projection_refs = _projection_refs_from_identity(staged_projection.get("component_identity"))
    output = compile_candidate(
        taxonomy_ref=taxonomy_ref,
        projection_refs=[dict(item) for item in projection_refs if isinstance(item, Mapping)],
        runtime_locale=control_locale_or_default(payload.get("runtime_locale"), taxonomy_ref.get("runtime_locale")),
        semantic_release_folder=str(payload.get("semantic_release_folder") or payload.get("target_semantic_release_folder") or "."),
        release_identity_policy=_mapping(payload, "release_identity_policy"),
    )
    output["release_ref"] = dict(output["release_ref"])
    return _owner_ok("compile_semantic_release_candidate", "semantic_release_domain_service", target_identity, output)


def materialize_semantic_release_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    output = materialize_candidate_release(payload)
    return _owner_ok("materialize_semantic_release_candidate", "semantic_release_domain_service", target_identity, output)


def merge_semantic_release_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    target_identity = _mapping(payload, "target_identity")
    output = merge_candidates(
        merge_run_id=str(payload.get("merge_run_id", "")),
        source_release_refs=[dict(item) for item in payload.get("source_release_refs", payload.get("source_releases", ())) if isinstance(item, Mapping)],
        projection_merge_mode=str(payload.get("projection_merge_mode") or ""),
    )
    return _owner_ok("merge_semantic_release_candidates", "multi_source_merge_domain_service", target_identity, output)
