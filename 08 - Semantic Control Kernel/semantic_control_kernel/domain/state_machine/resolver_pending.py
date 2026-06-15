from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.domain.state_machine.evidence import evidence_by_source
from semantic_control_kernel.domain.state_machine.models import StateEvidenceBundle, TargetIdentity
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore


def resolve_pending_refs(
    resume_store: WorkflowResumeStore | None,
    target_identity: TargetIdentity,
    bundle: StateEvidenceBundle,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pending_confirmation_refs: list[dict[str, Any]] = []
    pending_interaction_refs: list[dict[str, Any]] = []
    seen_confirmation_ids: set[str] = set()
    seen_interaction_ids: set[str] = set()

    def add_confirmation_ref(payload: Mapping[str, Any]) -> None:
        request_id = payload.get("confirmation_request_id")
        if not isinstance(request_id, str) or not request_id or request_id in seen_confirmation_ids:
            return
        ref = {"confirmation_request_id": request_id}
        workflow_run_id = payload.get("workflow_run_id")
        if isinstance(workflow_run_id, str) and workflow_run_id:
            ref["workflow_run_id"] = workflow_run_id
        pending_confirmation_refs.append(ref)
        seen_confirmation_ids.add(request_id)

    def add_interaction_ref(payload: Mapping[str, Any]) -> None:
        request_id = payload.get("interaction_request_id")
        if not isinstance(request_id, str) or not request_id or request_id in seen_interaction_ids:
            return
        ref = {"interaction_request_id": request_id}
        workflow_run_id = payload.get("workflow_run_id")
        if isinstance(workflow_run_id, str) and workflow_run_id:
            ref["workflow_run_id"] = workflow_run_id
        pending_interaction_refs.append(ref)
        seen_interaction_ids.add(request_id)

    resume_payloads: list[dict[str, Any]] = []
    if resume_store is not None:
        for resume_state in resume_store.list_resumable(target_identity.to_dict()):
            resume_payloads.append(resume_state.to_dict())
    resume_payloads.extend(
        ref.payload_ref
        for ref in evidence_by_source(bundle, "kernel_store_resume_state", target_identity=target_identity)
    )
    for payload in resume_payloads:
        for item in payload.get("pending_confirmation_refs", ()):
            if isinstance(item, Mapping):
                add_confirmation_ref(item)
        for item in payload.get("pending_interaction_refs", ()):
            if isinstance(item, Mapping):
                add_interaction_ref(item)

    for ref in evidence_by_source(bundle, "kernel_store_pending_confirmations", target_identity=target_identity):
        payload = ref.payload_ref
        request_payload = payload.get("confirmation_request") if isinstance(payload.get("confirmation_request"), Mapping) else payload
        if isinstance(request_payload, Mapping):
            add_confirmation_ref(request_payload)

    return pending_confirmation_refs, pending_interaction_refs


__all__ = ["resolve_pending_refs"]
