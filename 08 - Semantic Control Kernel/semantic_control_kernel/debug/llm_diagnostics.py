from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.debug.redaction import RedactionEngine, RedactionProfile
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id, require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.validation.debug_validation import validate_llm_attempt_diagnostic


def _validate_llm_diagnostic_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("LLM attempt diagnostic must be an object.")
    validate_llm_attempt_diagnostic(payload)


class LLMAttemptDiagnosticRecorder:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "llm_attempt_diagnostics")
        self._trace_store = TraceLinkStore(paths)
        self._redaction = RedactionEngine(state_root=paths.state_root)

    def record_failed_attempt(
        self,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        analysis_run_id: str,
        llm_function_name: str,
        attempt_index: int,
        max_attempts: int,
        attempted_schema: str,
        parse_status: str,
        validation_status: str,
        validation_error_summary: str,
        artifact_refs: Mapping[str, Any],
    ) -> dict[str, Any]:
        trace_context = self._trace_store.ensure_trace_context(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            started_by="llm_diagnostics",
            root_target_identity_ref=f"workflow_runs/active/{workflow_run_id}.json#target_identity",
            state_root_ref="state",
        )
        payload = {
            "schema_version": "debug.llm_attempt_diagnostic.v1",
            "llm_attempt_id": generate_id("llm_attempt_id"),
            "trace_id": trace_context["trace_id"],
            "workflow_run_id": workflow_run_id,
            "analysis_run_id": analysis_run_id,
            "llm_function_name": llm_function_name,
            "attempt_index": attempt_index,
            "max_attempts": max_attempts,
            "attempted_schema": attempted_schema,
            "parse_status": parse_status,
            "validation_status": validation_status,
            "validation_error_summary": self._redaction.safe_summary(validation_error_summary),
            "artifact_refs": dict(artifact_refs),
            "created_at": utc_iso(),
            "redaction_profile": self._redaction.profile_payload(RedactionProfile.SUPPORT_SAFE_V1),
        }
        run_dir = self.paths.state_root / "debug" / "llm_attempts" / require_state_id("analysis_run_id", analysis_run_id)
        diagnostic_path = run_dir / f"{attempt_index:06d}_{payload['llm_attempt_id']}.json"
        self._json.write_json(diagnostic_path, payload, immutable=True, validator=_validate_llm_diagnostic_payload)
        self._trace_store.append_link(
            workflow_run_id=workflow_run_id,
            object_kind="llm_attempt_diagnostic",
            object_id=payload["llm_attempt_id"],
            object_ref=self.paths.relative_to_state_root(diagnostic_path),
        )
        for ref_name, ref_value in artifact_refs.items():
            if isinstance(ref_value, str):
                self._trace_store.append_link(
                    workflow_run_id=workflow_run_id,
                    object_kind="llm_attempt_artifact",
                    object_id=f"{payload['llm_attempt_id']}:{ref_name}",
                    object_ref=ref_value,
                )
        KernelStateHardCapService(self.paths).prune_debug_llm_runs()
        return payload
