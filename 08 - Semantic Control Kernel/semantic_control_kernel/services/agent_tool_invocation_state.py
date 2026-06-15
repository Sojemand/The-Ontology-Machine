from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.resume_store import WorkflowResumeStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore


def active_run_summaries(store: WorkflowRunStore | None) -> list[dict[str, Any]]:
    if store is None:
        return []
    return [workflow_run_summary(record) for record in store.list_active_runs()]


def workflow_run_summary(record: Any) -> dict[str, Any]:
    payload = record.to_dict()
    return {
        "workflow_ref": opaque_ref(str(payload["workflow_run_id"])),
        "workflow_tool": payload["workflow_tool"],
        "status": payload["status"],
        "updated_at": payload["updated_at"],
    }


def resumable_count(store: WorkflowResumeStore | None) -> int:
    return len(store.list_resumable()) if store is not None else 0


def pending_interaction_count(store: InteractionRequestStore | None) -> int:
    if store is None:
        return 0
    return len(tuple(store.paths.pending_interactions_active_dir.glob("*.json")))


def pending_interactions_for_workflow(store: InteractionRequestStore | None, workflow_run_id: str) -> list[Any]:
    if store is None:
        return []
    return store.list_pending_interactions_for_workflow(workflow_run_id)


def opaque_ref(value: str) -> str:
    return "opaque:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def snapshot_state_files(state_root: Path) -> dict[str, str]:
    if not state_root.exists():
        return {}
    return {
        path.relative_to(state_root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(state_root.rglob("*"))
        if path.is_file()
    }


def stable_json_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
