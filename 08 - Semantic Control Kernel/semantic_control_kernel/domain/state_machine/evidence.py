from __future__ import annotations

from typing import Any, Iterable, Mapping

from semantic_control_kernel.domain.state_machine.identity import build_target_identity
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, StateEvidenceRef, TargetIdentity, TargetSelector


EVIDENCE_SOURCES = (
    "kernel_store_binding",
    "kernel_store_attach_state",
    "kernel_store_locks",
    "kernel_store_pending_confirmations",
    "kernel_store_resume_state",
    "kernel_store_receipts",
    "artifact_tree_folder_contract",
    "database_content_summary",
    "pipeline_semantic_status",
    "pipeline_active_release",
    "pipeline_batch_manifest",
    "pipeline_materialization_refs",
)

FALSE_FRIEND_EVIDENCE_SOURCES = (
    "inspect_active_corpus",
    "old_corpus_builder_context",
    "orchestrator_ui_state",
)

TRUST_CLASSES = (
    "kernel_authoring_truth",
    "owner_read_evidence",
    "filesystem_evidence",
    "test_fixture_evidence",
)


def coerce_evidence_bundle(value: StateEvidenceBundle | Mapping[str, Any] | None, target_selector: TargetSelector | Mapping[str, Any]) -> StateEvidenceBundle:
    if isinstance(value, StateEvidenceBundle):
        return value
    if isinstance(value, Mapping):
        return StateEvidenceBundle.from_dict(value)
    selector = target_selector if isinstance(target_selector, TargetSelector) else TargetSelector.from_dict(target_selector)
    return StateEvidenceBundle(
        evidence_bundle_id="evidence_empty",
        created_at="",
        target_selector=selector,
        evidence_refs=(),
    )


def evidence_by_kind(
    bundle: StateEvidenceBundle,
    kind: str,
    *,
    target_identity: TargetIdentity | None = None,
) -> tuple[StateEvidenceRef, ...]:
    return tuple(
        ref
        for ref in bundle.evidence_refs
        if ref.kind == kind
        and not is_false_friend(ref)
        and (target_identity is None or evidence_matches_target(ref, target_identity))
    )


def evidence_by_source(
    bundle: StateEvidenceBundle,
    source: str,
    *,
    target_identity: TargetIdentity | None = None,
) -> tuple[StateEvidenceRef, ...]:
    return tuple(
        ref
        for ref in bundle.evidence_refs
        if ref.source == source
        and not is_false_friend(ref)
        and (target_identity is None or evidence_matches_target(ref, target_identity))
    )


def first_evidence(
    bundle: StateEvidenceBundle,
    *,
    kind: str | None = None,
    source: str | None = None,
    target_identity: TargetIdentity | None = None,
) -> StateEvidenceRef | None:
    for ref in bundle.evidence_refs:
        if is_false_friend(ref):
            continue
        if kind is not None and ref.kind != kind:
            continue
        if source is not None and ref.source != source:
            continue
        if target_identity is not None and not evidence_matches_target(ref, target_identity):
            continue
        return ref
    return None


def evidence_ref_ids(refs: Iterable[StateEvidenceRef]) -> tuple[str, ...]:
    return tuple(ref.evidence_ref_id for ref in refs if not is_false_friend(ref))


def evidence_matches_target(ref: StateEvidenceRef, target_identity: TargetIdentity) -> bool:
    if not ref.target_identity:
        return True
    ref_target = build_target_identity(ref.target_identity, created_from="evidence_ref")
    target = target_identity.to_dict()
    ref_payload = ref.target_identity
    comparable_keys = {
        "target_hash": ("target_hash",),
        "database_path_hash": ("database_path_hash", "database_path"),
        "artifact_root_path_hash": ("artifact_root_path_hash", "artifact_root_path"),
        "database_id": ("database_id",),
        "release_fingerprint": ("release_fingerprint", "semantic_release_fingerprint"),
        "semantic_release_identity_hash": ("semantic_release_identity_hash",),
        "taxonomy_fingerprint": ("taxonomy_fingerprint",),
        "projection_set_hash": ("projection_set_hash", "projection_fingerprints", "active_projections"),
        "pipeline_batch_id": ("pipeline_batch_id",),
        "source_database_set_hash": ("source_database_set_hash", "source_database_ids", "selected_source_database_ids", "source_databases"),
    }
    comparisons = []
    ref_target_payload = ref_target.to_dict()
    for key, source_keys in comparable_keys.items():
        if not any(ref_payload.get(source_key) for source_key in source_keys):
            continue
        ref_value = ref_target_payload.get(key)
        target_value = target.get(key)
        if not ref_value or not target_value:
            return False
        comparisons.append(ref_value == target_value)
    return bool(comparisons) and all(comparisons)


def is_false_friend(ref: StateEvidenceRef) -> bool:
    return ref.source in FALSE_FRIEND_EVIDENCE_SOURCES


def payload(ref: StateEvidenceRef | None) -> dict[str, Any]:
    return ref.payload_ref.copy() if ref is not None else {}
