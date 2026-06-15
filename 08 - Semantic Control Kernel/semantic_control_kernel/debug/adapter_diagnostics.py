from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.debug.redaction import RedactionEngine, RedactionProfile
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import require_state_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.repository.trace_store import TraceLinkStore
from semantic_control_kernel.validation.debug_validation import validate_adapter_call_diagnostic


def _validate_adapter_diagnostic_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("Adapter call diagnostic must be an object.")
    validate_adapter_call_diagnostic(payload)


class AdapterDiagnosticRecorder:
    def __init__(self, paths: StatePaths) -> None:
        self.paths = paths
        self._json = AtomicJsonStore(paths, "adapter_diagnostics")
        self._trace_store = TraceLinkStore(paths)
        self._redaction = RedactionEngine(state_root=paths.state_root)

    def record_result(
        self,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        adapter_name: str,
        owner_module: str,
        owner_action: str,
        adapter_call_id: str,
        status: str,
        started_at: str,
        request_ref: str,
        response_ref: str,
        mutating: bool = False,
        diagnostics: list[Mapping[str, Any]] | None = None,
        target_identity: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        trace_context = self._trace_store.ensure_trace_context(
            workflow_run_id=workflow_run_id,
            workflow_tool=workflow_tool,
            started_by="adapter_diagnostics",
            root_target_identity_ref=f"workflow_runs/active/{workflow_run_id}.json#target_identity",
            state_root_ref="state",
        )
        finished_at = utc_iso()
        mapped_status = _map_status(status, mutating=mutating)
        safe_summary = self._redaction.safe_summary(f"{adapter_name} -> {owner_module}.{owner_action} finished with {mapped_status}.")
        payload = {
            "schema_version": "debug.adapter_call_diagnostic.v1",
            "adapter_call_id": adapter_call_id,
            "trace_id": trace_context["trace_id"],
            "workflow_run_id": workflow_run_id,
            "adapter_name": adapter_name,
            "owner_module": owner_module,
            "owner_action": owner_action,
            "status": mapped_status,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": _duration_ms(started_at, finished_at),
            "safe_summary": safe_summary,
            "request_ref": request_ref,
            "response_ref": response_ref,
            "redaction_profile": self._redaction.profile_payload(RedactionProfile.SUPPORT_SAFE_V1),
        }
        if diagnostics:
            first = next((item for item in diagnostics if isinstance(item, Mapping)), None)
            if first is not None and isinstance(first.get("code"), str):
                payload["error_code"] = str(first["code"])
        if target_identity:
            payload["target_identity_hash"] = str(target_identity.get("target_hash") or target_identity.get("database_path_hash") or "")

        workflow_id = require_state_id("workflow_run_id", workflow_run_id)
        call_id = require_state_id("adapter_call_id", adapter_call_id)
        run_dir = self.paths.state_root / "debug" / "adapter_calls" / workflow_id
        sequence_index = _next_sequence_index(run_dir)
        diagnostic_path = run_dir / f"{sequence_index:06d}_{call_id}.json"
        self._json.write_json(diagnostic_path, payload, immutable=True, validator=_validate_adapter_diagnostic_payload)
        self._trace_store.append_link(
            workflow_run_id=workflow_run_id,
            object_kind="adapter_call_diagnostic",
            object_id=adapter_call_id,
            object_ref=self.paths.relative_to_state_root(diagnostic_path),
        )
        KernelStateHardCapService(self.paths).prune_debug_adapter_workflows()
        return payload


def _map_status(status: str, *, mutating: bool) -> str:
    if status == "ok":
        return "succeeded"
    if status == "missing_capability":
        return "missing_capability"
    if status == "timeout":
        return "timed_out"
    if status in {"blocked_by_kernel_precondition", "target_identity_changed", "target_identity_unproven"}:
        return "blocked"
    if mutating and status in {"owner_error", "invalid_owner_response"}:
        return "uncertain_partial_mutation"
    return "failed"


def _duration_ms(started_at: str, finished_at: str) -> int:
    return max(0, int((_parse_utc(finished_at) - _parse_utc(started_at)).total_seconds() * 1000))


def _next_sequence_index(run_dir: Path) -> int:
    if not run_dir.exists():
        return 1
    indexes = []
    for path in run_dir.glob("*.json"):
        prefix = path.name.split("_", 1)[0]
        if prefix.isdigit():
            indexes.append(int(prefix))
    return (max(indexes) + 1) if indexes else 1


def _parse_utc(value: str):
    from datetime import datetime, timezone

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
