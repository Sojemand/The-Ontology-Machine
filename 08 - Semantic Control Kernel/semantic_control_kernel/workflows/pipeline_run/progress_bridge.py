from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.event_store import ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths, stable_hash, utc_iso
from semantic_control_kernel.types.enums import ProgressEventType, ProgressStatus
from semantic_control_kernel.types.events import ProgressEvent
from semantic_control_kernel.workflows.pipeline_run.progress_stage_rows import (
    stage_artifact_refs,
    state_summary,
    visible_summary,
)


class OrchestratorSnapshotProgressBridge:
    def __init__(
        self,
        state_paths: StatePaths,
        *,
        workflow_run_id: str,
        workflow_tool: str,
        snapshot_path: str | Path,
    ) -> None:
        self.state_paths = state_paths
        self.workflow_run_id = workflow_run_id
        self.workflow_tool = workflow_tool
        self.snapshot_path = Path(snapshot_path)
        self._store = ProgressEventStore(state_paths)
        self._last_signature = ""

    def poll(self) -> None:
        snapshot = self._read_snapshot()
        if not snapshot:
            return
        signature = stable_hash(json.dumps(snapshot, sort_keys=True, ensure_ascii=True, default=str))
        if signature == self._last_signature:
            return
        payload = {
            "schema_version": ProgressEvent.SCHEMA_VERSION,
            "workflow_run_id": self.workflow_run_id,
            "workflow_tool": self.workflow_tool,
            "step_id": "orchestrator.snapshot",
            "step_label": "Orchestrator",
            "event_type": ProgressEventType.PIPELINE_STEP.value,
            "status": _progress_status(snapshot),
            "user_visible_summary": visible_summary(snapshot),
            "current_state_summary": state_summary(snapshot),
            "timestamp": utc_iso(),
        }
        stage_refs = stage_artifact_refs(snapshot)
        if stage_refs:
            payload["artifact_refs"] = stage_refs
        self._store.append_progress_event_with_next_sequence(payload)
        self._last_signature = signature

    def _read_snapshot(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return dict(payload) if isinstance(payload, Mapping) else {}


def pipeline_snapshot_path(
    state_paths: StatePaths,
    workflow_run_id: str,
    pipeline_batch_id: str,
    *,
    artifact_root: str | Path,
) -> Path:
    state_paths.ensure_layout()
    return Path(artifact_root) / ".kernel" / "orchestrator_snapshots" / workflow_run_id / f"{pipeline_batch_id}.json"


def _progress_status(snapshot: Mapping[str, Any]) -> str:
    if bool(snapshot.get("is_running")):
        return ProgressStatus.STEP_STARTED.value
    if bool(snapshot.get("aborted")):
        return ProgressStatus.FAILED.value
    return ProgressStatus.COMPLETED.value
