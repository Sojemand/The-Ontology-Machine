from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from semantic_control_kernel.repository.paths import StatePaths, stable_hash, utc_iso
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore

from .paths import MODULE_ROOT, _write_json


@dataclass(frozen=True)
class _EventAck:
    payload: dict[str, Any]


@dataclass
class _Phase20EventSink:
    host_surface_identity: str = "client_frontend_http_pipeline_session"

    def emit(self, event: Any) -> _EventAck:
        return _EventAck(
            {
                "accepted": True,
                "acknowledged_at": utc_iso(),
                "frontend_event_id": event.payload["frontend_event_id"],
                "host_surface_identity": self.host_surface_identity,
                "schema_version": "kernel.client_frontend_event_ack.v1",
            }
        )


def _phase20_state_paths(state_paths: StatePaths | None = None) -> StatePaths:
    paths = state_paths or StatePaths.from_module_root(MODULE_ROOT)
    paths.ensure_layout()
    return paths


def _phase20_target_identity(run_id: str, purpose: str) -> dict[str, str]:
    return {
        "target_hash": f"tgt_{stable_hash(f'{run_id}:{purpose}')}",
        "artifact_root_path_hash": f"art_{stable_hash(f'{purpose}:{run_id}')}",
    }


def _phase20_state_snapshot_identity(run_id: str, purpose: str) -> dict[str, str]:
    return {"state_snapshot_id": f"ss_{stable_hash(f'{run_id}:{purpose}')}"} 


def _phase20_expiry(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def _create_phase20_support_bundle(
    state_paths: StatePaths,
    run_id: str,
    *,
    workflow_tool: str = "create_custom_projection_path",
) -> dict[str, Any]:
    paths = _phase20_state_paths(state_paths)
    workflow_run = WorkflowRunStore(paths).create_run(
        workflow_tool,
        _phase20_target_identity(run_id, workflow_tool),
        "phase20_go_live",
    )
    validation_report_path = paths.safe_path(
        "debug",
        "llm_attempts",
        workflow_run.workflow_run_id,
        "attempt_03",
        "validation_report.json",
    )
    validation_report_ref = paths.relative_to_state_root(validation_report_path)
    _write_json(
        validation_report_path,
        {
            "schema_version": "debug.llm_validation_report.v1",
            "analysis_run_id": f"anl_{stable_hash(workflow_run.workflow_run_id)}",
            "attempt_index": 3,
            "attempted_schema": "semantic_control_kernel.phase20.final_llm_validation.v1",
            "validation_error_summary": "Structured JSON validation failed after the final retry attempt.",
            "workflow_run_id": workflow_run.workflow_run_id,
        },
    )
    workflow_run_ref = paths.relative_to_state_root(
        paths.workflow_runs_active_dir / f"{workflow_run.workflow_run_id}.json"
    )
    store = SupportBundleStore(paths)
    support_ref = store.write_support_bundle(
        category="final_llm_validation_failure",
        workflow_run_id=workflow_run.workflow_run_id,
        recovery_event_id=f"rev_{stable_hash(f'{run_id}:{workflow_tool}:support')}",
        summary="Kernel final LLM validation failure support bundle with redacted runtime diagnostics only.",
        workflow_tool=workflow_run.workflow_tool,
        included_refs=[validation_report_ref, workflow_run_ref],
        user_visible_cause="The Kernel exhausted its internal retry budget before it could validate the structured LLM result.",
        what_was_preserved="The active workflow state and prior artifacts remain intact for diagnosis and safe retry decisions.",
        what_was_not_changed="No partial or hand-repaired LLM output was promoted into downstream mutation paths.",
        created_by="phase20_go_live",
    )
    support_bundle_id = str(support_ref.payload["support_bundle_id"])
    manifest = store.get_manifest(support_bundle_id)
    file_refs = store.bundle_file_refs(support_bundle_id)
    return {
        "workflow_run_id": workflow_run.workflow_run_id,
        "workflow_tool": workflow_run.workflow_tool,
        "target_identity": dict(workflow_run.target_identity),
        "support_bundle_ref": support_ref.to_dict(),
        "bundle_file_refs": file_refs,
        "manifest": manifest,
        "validation_report_ref": validation_report_ref,
        "workflow_run_ref": workflow_run_ref,
    }


def _phase20_support_only_option(
    *,
    recovery_id: str,
    recovery_event_id: str,
    target_identity: dict[str, Any],
    state_snapshot_identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "kernel.recovery_option.v1",
        "recovery_id": recovery_id,
        "recovery_event_id": recovery_event_id,
        "label": "Open support bundle",
        "description": "Open the redacted support bundle for the final Kernel failure.",
        "owner": "support_surface",
        "recovery_action_type": "open_support_bundle",
        "effect": "open_support_bundle",
        "risk_class": "support",
        "target_identity": target_identity,
        "state_snapshot_identity": state_snapshot_identity,
        "agent_tool": "kernel_open_support_bundle",
        "kernel_dialog_action": "support_bundle_dialog",
        "starts_new_workflow": False,
        "continuation_workflow_tool": None,
        "requires_confirmation": False,
        "expires_at": _phase20_expiry(),
    }
