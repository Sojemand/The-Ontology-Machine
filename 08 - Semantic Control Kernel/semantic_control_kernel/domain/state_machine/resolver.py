from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evidence import (
    coerce_evidence_bundle,
    evidence_ref_ids,
    is_false_friend,
)
from semantic_control_kernel.domain.state_machine.identity import build_target_identity
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetSelector
from semantic_control_kernel.domain.state_machine.resolver_binding import resolve_binding
from semantic_control_kernel.domain.state_machine.resolver_pending import resolve_pending_refs
from semantic_control_kernel.domain.state_machine.resolver_release import (
    resolve_active_release,
    resolve_attached_release,
    resolve_semantic_release_state,
)
from semantic_control_kernel.domain.state_machine.resolver_support import state_snapshot_id
from semantic_control_kernel.domain.state_machine.resolver_target import (
    resolve_artifact_tree,
    resolve_database,
    resolve_database_emptiness,
    resolve_locks,
)
from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.database_binding_registry import DatabaseArtifactBindingRegistry
from semantic_control_kernel.repository.lock_store import LockStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.types.state import ActiveDatabaseState


class KernelStateResolver:
    def __init__(
        self,
        *,
        state_paths: StatePaths | None = None,
        lock_store: LockStore | None = None,
        binding_registry: DatabaseArtifactBindingRegistry | None = None,
        attach_state_store: AttachStateStore | None = None,
        resume_store: WorkflowResumeStore | None = None,
    ) -> None:
        self.state_paths = state_paths
        self.lock_store = lock_store or (LockStore(state_paths) if state_paths is not None else None)
        self.binding_registry = binding_registry or (
            DatabaseArtifactBindingRegistry(state_paths) if state_paths is not None else None
        )
        self.attach_state_store = attach_state_store or (AttachStateStore(state_paths) if state_paths is not None else None)
        self.resume_store = resume_store or (WorkflowResumeStore(state_paths) if state_paths is not None else None)

    def resolve(
        self,
        target_selector: TargetSelector | Mapping[str, Any],
        evidence_bundle: StateEvidenceBundle | Mapping[str, Any] | None,
        now_utc: datetime,
    ) -> ActiveDatabaseState:
        selector = target_selector if isinstance(target_selector, TargetSelector) else TargetSelector.from_dict(target_selector)
        bundle = coerce_evidence_bundle(evidence_bundle, selector)
        target_identity = build_target_identity(selector)
        blocking: list[dict[str, Any]] = []

        active_lock_refs = resolve_locks(self.lock_store, target_identity, bundle, now_utc, blocking)
        binding = resolve_binding(self.binding_registry, selector, target_identity, bundle, blocking)
        artifact_tree = resolve_artifact_tree(selector, target_identity, bundle, binding, blocking)
        active_database = resolve_database(selector, target_identity, bundle, binding, blocking)
        database_emptiness = resolve_database_emptiness(target_identity, bundle, active_database, blocking)
        attached_release = resolve_attached_release(self.attach_state_store, target_identity, bundle, blocking)
        active_release = resolve_active_release(target_identity, bundle, attached_release, blocking)
        semantic_state = resolve_semantic_release_state(
            target_identity,
            active_database,
            attached_release,
            active_release,
            bundle,
            blocking,
        )
        pending_confirmation_refs, pending_interaction_refs = resolve_pending_refs(self.resume_store, target_identity, bundle)
        evidence_ids = evidence_ref_ids(tuple(ref for ref in bundle.evidence_refs if not is_false_friend(ref)))
        snapshot_id = state_snapshot_id(
            target_identity,
            database_emptiness,
            semantic_state,
            blocking,
            active_lock_refs,
            evidence_ids,
            now_utc,
        )
        for index, blocker in enumerate(blocking):
            blocker["state_snapshot_id"] = snapshot_id
            blocker.setdefault("evidence_refs", list(evidence_ids))
            blocking[index] = blocker

        payload = {
            "schema_version": ActiveDatabaseState.SCHEMA_VERSION,
            "state_snapshot_id": snapshot_id,
            "artifact_tree": artifact_tree,
            "active_database": active_database,
            "database_emptiness": database_emptiness,
            "semantic_release_state": semantic_state,
            "blocking_reasons": blocking,
            "active_lock_refs": active_lock_refs,
            "pending_confirmation_refs": pending_confirmation_refs,
            "pending_interaction_refs": pending_interaction_refs,
            "evidence_refs": list(evidence_ids),
        }
        if attached_release:
            payload["attached_release"] = attached_release
        if active_release:
            payload["active_release"] = active_release
        runtime_locale = (active_release or attached_release or {}).get("runtime_locale")
        if runtime_locale:
            payload["runtime_locale"] = runtime_locale
        return ActiveDatabaseState.from_dict(payload)
