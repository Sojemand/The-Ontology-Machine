from __future__ import annotations

from typing import Any, Mapping, Sequence


class SupportBundleBuilder:
    def __init__(self, support_bundle_store) -> None:
        self.store = support_bundle_store

    def build_for_final_error(self, **kwargs: Any):
        return self._build(retention_class="final_error_manual", **kwargs)

    def build_for_recovery_event(self, **kwargs: Any):
        return self._build(retention_class="support_only_manual", **kwargs)

    def build_for_failed_adapter_call(self, **kwargs: Any):
        return self._build(retention_class="support_only_manual", **kwargs)

    def build_for_final_llm_validation_failure(self, **kwargs: Any):
        return self._build(retention_class="llm_validation_manual", **kwargs)

    def build_for_stale_recovery_rejection(self, **kwargs: Any):
        return self._build(retention_class="stale_recovery_90_days", **kwargs)

    def _build(
        self,
        *,
        trace_context: Mapping[str, Any] | None = None,
        workflow_run_id: str,
        category: str,
        severity: str,
        safe_summary: str,
        user_visible_cause: str,
        redaction_profile: Mapping[str, Any],
        included_refs: Sequence[Mapping[str, Any] | str],
        retention_class: str,
        workflow_tool: str | None = None,
        failed_kernel_step: str | None = None,
        recovery_event_id: str | None = None,
        mirror_event_id: str | None = None,
        state_snapshot_identity: Mapping[str, Any] | None = None,
        target_identity: Mapping[str, Any] | None = None,
        what_was_preserved: str | None = None,
        what_was_not_changed: str | None = None,
        receipt_refs: Sequence[Mapping[str, Any]] = (),
        progress_event_refs: Sequence[Mapping[str, Any]] = (),
        mirror_event_refs: Sequence[Mapping[str, Any]] = (),
        adapter_call_diagnostic_refs: Sequence[Mapping[str, Any]] = (),
        llm_attempt_diagnostic_refs: Sequence[Mapping[str, Any]] = (),
        failed_attempt_artifact_refs: Sequence[Mapping[str, Any]] = (),
        created_by: str | None = None,
    ):
        return self.store.write_support_bundle(
            category=category,
            workflow_run_id=workflow_run_id,
            recovery_event_id=recovery_event_id,
            summary=safe_summary,
            included_refs=included_refs,
            support_bundle_id=None,
            technical_context={
                "trace_context": dict(trace_context or {}),
                "user_visible_cause": user_visible_cause,
                "what_was_preserved": what_was_preserved,
                "what_was_not_changed": what_was_not_changed,
            },
            workflow_tool=workflow_tool or str((trace_context or {}).get("workflow_tool") or "unknown_workflow"),
            severity=severity,
            retention_class=retention_class,
            mirror_event_id=mirror_event_id,
            failed_kernel_step=failed_kernel_step,
            user_visible_cause=user_visible_cause,
            state_snapshot_identity=state_snapshot_identity,
            target_identity=target_identity,
            what_was_preserved=what_was_preserved,
            what_was_not_changed=what_was_not_changed,
            related_receipt_refs=receipt_refs,
            related_progress_event_refs=progress_event_refs,
            related_mirror_event_refs=mirror_event_refs,
            adapter_call_diagnostic_refs=adapter_call_diagnostic_refs,
            llm_attempt_diagnostic_refs=llm_attempt_diagnostic_refs,
            failed_attempt_artifact_refs=failed_attempt_artifact_refs,
            redaction_profile=dict(redaction_profile),
            created_by=created_by,
        )
