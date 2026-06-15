from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evidence import first_evidence
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetIdentity
from semantic_control_kernel.domain.state_machine.resolver_support import blocker_payload, has_blocker, release_complete
from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.types.enums import SemanticReleaseState


def resolve_attached_release(
    attach_state_store: AttachStateStore | None,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    blocking: list[dict[str, Any]],
) -> dict[str, Any] | None:
    attach = None
    if attach_state_store is not None:
        state = attach_state_store.get_attach_state_for_database(target_identity.to_dict())
        attach = state.to_dict() if state is not None else None
    evidence_attach = first_evidence(bundle, kind="semantic_release_attach_state", source="kernel_store_attach_state")
    if evidence_attach is not None:
        attach = evidence_attach.payload_ref
    if attach is not None and attach.get("written_release_exists") is False:
        blocking.append(blocker_payload("release_not_written", target_identity, "written release artifact", "missing", ()))
    return deepcopy(attach)


def resolve_active_release(
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
    attached_release: Mapping[str, Any] | None,
    blocking: list[dict[str, Any]],
) -> dict[str, Any] | None:
    ref = first_evidence(bundle, kind="pipeline_active_release", target_identity=target_identity)
    if ref is None:
        return None
    active = deepcopy(ref.payload_ref)
    fingerprint = active.get("release_fingerprint")
    if active.get("exists") and not fingerprint:
        blocking.append(blocker_payload("target_identity_changed", target_identity, "active release fingerprint", "missing", (ref.evidence_ref_id,)))
        return active
    if attached_release and fingerprint and attached_release.get("release_fingerprint") and attached_release["release_fingerprint"] != fingerprint:
        blocking.append(blocker_payload("target_identity_changed", target_identity, "attached release fingerprint", "active release mismatch", (ref.evidence_ref_id,)))
    return active


def resolve_semantic_release_state(
    target_identity: TargetIdentity,
    active_database: Mapping[str, Any],
    attached_release: Mapping[str, Any] | None,
    active_release: Mapping[str, Any] | None,
    bundle: StateEvidenceBundle,
    blocking: list[dict[str, Any]],
) -> str:
    if has_blocker(blocking, "target_identity_changed", "release_not_written", "owner_evidence_conflict"):
        return SemanticReleaseState.UNKNOWN.value
    if active_release and active_release.get("exists", True):
        if release_complete(active_release):
            return SemanticReleaseState.SEMANTIC_RELEASE_ACTIVE.value
        blocking.append(blocker_payload("release_incomplete", target_identity, "active release completeness", "incomplete", ()))
        return SemanticReleaseState.SEMANTIC_RELEASE_INCOMPLETE.value
    if attached_release:
        if release_complete(attached_release) and attached_release.get("written_release_exists", True):
            return SemanticReleaseState.SEMANTIC_RELEASE_COMPLETE_NOT_ACTIVE.value
        blocking.append(blocker_payload("release_incomplete", target_identity, "attached release completeness", "incomplete", ()))
        return SemanticReleaseState.SEMANTIC_RELEASE_INCOMPLETE.value
    staged = first_evidence(bundle, kind="staged_semantic_release", target_identity=target_identity)
    if staged is not None:
        return SemanticReleaseState.SEMANTIC_RELEASE_INCOMPLETE.value
    if active_database.get("database_exists"):
        return SemanticReleaseState.NO_SEMANTIC_RELEASE.value
    return SemanticReleaseState.UNKNOWN.value


__all__ = [
    "resolve_active_release",
    "resolve_attached_release",
    "resolve_semantic_release_state",
]
