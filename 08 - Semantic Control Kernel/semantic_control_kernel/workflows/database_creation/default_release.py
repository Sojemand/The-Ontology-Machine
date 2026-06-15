from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker
from semantic_control_kernel.types.database_creation import DatabaseCreationTarget, DefaultSemanticReleaseRef
from semantic_control_kernel.workflows.database_creation.default_release_payload import default_release_payload_from_adapter_output
from semantic_control_kernel.workflows.database_creation.shared_steps import adapter_output, create_blocker


def export_default_release(
    adapter: Any,
    *,
    target: DatabaseCreationTarget,
    blueprint_ref: str,
) -> DefaultSemanticReleaseRef | MissingCapabilityBlocker:
    result = adapter.export_default_semantic_release(
        {
            "blueprint_ref": blueprint_ref,
            "target_identity": target.target_identity,
            "semantic_release_path": target.semantic_release_path,
        }
    )
    if isinstance(result, MissingCapabilityBlocker):
        return result
    output = adapter_output(result)
    if not output and isinstance(result, AdapterCallResult):
        output = result.to_dict()
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        output = default_release_payload_from_adapter_output(output)
        receipt_ref = output.get("source_adapter_receipt_ref")
        receipt_ref = dict(receipt_ref) if isinstance(receipt_ref, Mapping) else {}
        receipt_ref.setdefault("adapter_call_id", payload.get("adapter_call_id", ""))
        receipt_ref.setdefault("adapter_name", payload.get("adapter_name", ""))
        receipt_ref.setdefault("kernel_function", payload.get("kernel_function", ""))
        receipt_ref.setdefault("output_path", str(output.get("output_path") or ""))
        output["source_adapter_receipt_ref"] = receipt_ref
    return DefaultSemanticReleaseRef.from_mapping(output)


def validate_complete_default_release(release_ref: DefaultSemanticReleaseRef):
    if not release_ref.release_id or not release_ref.release_version:
        return _release_blocker("release_incomplete", "Default Semantic Release export did not include release identity.")
    if not release_ref.source_adapter_receipt_ref:
        return _release_blocker("release_incomplete", "Default Semantic Release export did not include source adapter receipt proof.")
    if not release_ref.taxonomy_ref:
        return _release_blocker("release_incomplete", "Default Semantic Release export did not include taxonomy proof.")
    for key in ("taxonomy_id", "taxonomy_fingerprint"):
        if not release_ref.taxonomy_ref.get(key):
            return _release_blocker("release_incomplete", f"Default Semantic Release taxonomy proof did not include {key}.")
    if not release_ref.projection_refs:
        return _release_blocker("release_incomplete", "Default Semantic Release export did not include projection proof.")
    for projection_ref in release_ref.projection_refs:
        if not projection_ref.get("projection_id"):
            return _release_blocker("release_incomplete", "Default Semantic Release projection proof did not include projection_id.")
        if not (projection_ref.get("projection_fingerprint") or projection_ref.get("projection_set_hash")):
            return _release_blocker("release_incomplete", "Default Semantic Release projection proof did not include a fingerprint.")
    if not release_ref.release_fingerprint:
        return _release_blocker("release_fingerprint_mismatch", "Default Semantic Release export did not include a release fingerprint.")
    return None


def _release_blocker(blocker_code: str, summary: str):
    return create_blocker(
        step_id="dc_export_default_release",
        function_or_route="export_default_semantic_release",
        blocker_code=blocker_code,
        recovery_state_class="semantic_release_incomplete_staged",
        summary=summary,
    )


def write_default_release(
    adapter: Any,
    *,
    target: DatabaseCreationTarget,
    release_ref: DefaultSemanticReleaseRef,
) -> AdapterCallResult | MissingCapabilityBlocker:
    release_dir = Path(target.semantic_release_path) / "releases" / release_ref.release_id
    return adapter.write_semantic_release(
        {
            "release_ref": release_ref.to_dict(),
            "release_path": str(release_dir),
            "semantic_release_path": target.semantic_release_path,
            "target_identity": target.target_identity,
        }
    )


def load_default_release_for_attach(
    adapter: Any,
    *,
    target: DatabaseCreationTarget,
    release_ref: DefaultSemanticReleaseRef,
    release_path: str,
) -> AdapterCallResult | MissingCapabilityBlocker:
    return adapter.load_semantic_release(
        {
            "release_ref": release_ref.to_dict(),
            "release_path": release_path,
            "corpus_db_path": target.database_path,
            "target_identity": target.target_identity,
            "write_global_mirrors": False,
        }
    )


def preflight_activation(
    adapter: Any,
    *,
    target: DatabaseCreationTarget,
    release_ref: DefaultSemanticReleaseRef | Mapping[str, Any],
    release_path: str,
) -> AdapterCallResult | MissingCapabilityBlocker:
    payload = release_ref.to_dict() if isinstance(release_ref, DefaultSemanticReleaseRef) else dict(release_ref)
    return adapter.preflight_semantic_release_activation(
        {
            "release_ref": payload,
            "release_path": release_path,
            "corpus_db_path": target.database_path,
            "target_identity": target.target_identity,
            "write_global_mirrors": False,
        }
    )


def activate_release(
    adapter: Any,
    *,
    target: DatabaseCreationTarget,
    release_ref: DefaultSemanticReleaseRef | Mapping[str, Any],
    release_path: str,
) -> AdapterCallResult | MissingCapabilityBlocker:
    payload = release_ref.to_dict() if isinstance(release_ref, DefaultSemanticReleaseRef) else dict(release_ref)
    return adapter.activate_semantic_release(
        {
            "release_ref": payload,
            "release_path": release_path,
            "corpus_db_path": target.database_path,
            "target_identity": target.target_identity,
            "write_global_mirrors": False,
        }
    )
