from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.event_store import MirrorEventStore, ProgressEventStore
from semantic_control_kernel.repository.paths import StatePaths
from phase12_frozen_artifacts import _artifact_json_contracts, _artifact_path_map
from phase12_frozen_inventory import FreezeRun

def _freeze_observation(run: FreezeRun, workflow_tool: str) -> dict[str, Any]:
    execution = run.execution
    path_map = _artifact_path_map(run.artifact_root)
    mirror_store = MirrorEventStore(StatePaths.from_state_root(execution.state_root))
    stored_mirrors = [
        mirror_store.get_mirror_event(event["mirror_event_id"]).to_dict()
        for event in execution.mirror_events
        if event.get("mirror_event_id")
    ]
    stored_progress = ProgressEventStore(StatePaths.from_state_root(execution.state_root)).list_progress_events(execution.workflow_run_id)
    return {
        "workflow_tool": workflow_tool,
        "execution_workflow_tool": execution.workflow_tool,
        "status": execution.status,
        "final_state": execution.final_state,
        "completed_step_ids": list(execution.completed_step_ids),
        "operation_log": list(execution.operation_log),
        "progress_statuses": _progress_statuses(execution.progress_events),
        "stored_progress_statuses": _progress_statuses([event.to_dict() for event in stored_progress]),
        "mirror_event_types": [event.get("event_type") for event in execution.mirror_events],
        "stored_mirror_event_types": [event.get("event_type") for event in stored_mirrors],
        "final_mirror": _final_mirror_summary(execution.mirror_events[-1] if execution.mirror_events else {}),
        "selection_route": _selection_route(execution),
        "adapter_calls": _adapter_calls(run.adapters),
        "artifact_files": sorted(path_map.values()),
        "artifact_json_contracts": _artifact_json_contracts(run.artifact_root, path_map),
        "attach_state": _attach_state_summary(execution),
        "live_path_assertions": _live_path_assertions(run, workflow_tool),
    }

def _adapter_calls(adapters: Mapping[str, Any]) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {}
    for name, adapter in adapters.items():
        value = getattr(adapter, "calls", [])
        normalized = []
        for item in value:
            if isinstance(item, tuple):
                normalized.append(item[0])
            elif isinstance(item, Mapping):
                normalized.append("<request_payload>")
            else:
                normalized.append(item)
        calls[name] = normalized
    return calls

def _progress_statuses(events: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{event.get('step_id')}:{event.get('status')}"
        for event in events
    ]

def _final_mirror_summary(event: Mapping[str, Any]) -> dict[str, Any]:
    detail = event.get("technical_detail_ref")
    completion = detail.get("workflow_completion") if isinstance(detail, Mapping) else {}
    if not isinstance(completion, Mapping):
        completion = {}
    return {
        "agent_response_mode": dict(event.get("agent_explanation_guidance") or {}).get("response_mode"),
        "allowed_agent_tools": list(event.get("allowed_agent_tools") or []),
        "detail_kind": detail.get("kind") if isinstance(detail, Mapping) else None,
        "merge_route": completion.get("merge_route"),
        "workflow_family": completion.get("workflow_family"),
        "workflow_tool": completion.get("workflow_tool"),
    }

def _selection_route(execution: Any) -> str:
    selection = getattr(execution, "selection", None)
    if isinstance(selection, Mapping):
        return str(selection.get("merge_route") or "")
    return ""

def _attach_state_summary(execution: Any) -> dict[str, Any]:
    target = getattr(execution, "target", None)
    if target is not None:
        identity = target.target_identity
    elif isinstance(getattr(execution, "selection", None), Mapping):
        identity = {"database_path": execution.selection.get("target_database_path", "")}
    elif getattr(execution, "target_database_path", ""):
        identity = {"database_path": execution.target_database_path}
    else:
        identity = {}
    attach = AttachStateStore(StatePaths.from_state_root(execution.state_root)).get_attach_state_for_database(identity)
    if attach is None:
        return {"present": False}
    payload = attach.to_dict()
    return {
        "pointer_owner": payload.get("pointer_owner"),
        "present": True,
        "release_fingerprint": payload.get("release_fingerprint"),
        "release_id": payload.get("release_id"),
    }

def _live_path_assertions(run: FreezeRun, workflow_tool: str) -> dict[str, bool]:
    root = run.artifact_root
    execution = run.execution
    checks = {
        "artifact_root_exists": root.is_dir(),
        "target_database_exists": _target_database_path(execution).is_file(),
    }
    if workflow_tool in {"database_merge_additive_only", "empty_databases_merge_path", "filled_databases_merge_path"}:
        checks["merge_selection_exists"] = (root / "Documents" / "logs" / "merge_runs" / execution.merge_run_id / "merge_selection.json").is_file()
        checks["merge_collision_manifest_exists"] = (root / "Documents" / "logs" / "merge_runs" / execution.merge_run_id / "merge_collision_manifest.json").is_file()
        checks["release_bundle_exists"] = (root / "Semantic Release" / "releases" / "merged.release" / "release.json").is_file()
    if workflow_tool == "filled_databases_merge_path":
        checks["merge_id_map_exists"] = (root / "Documents" / "logs" / "merge_runs" / execution.merge_run_id / "merge_id_map.json").is_file()
    if workflow_tool == "database_rebuild_from_artifacts":
        checks["rebuild_manifest_exists"] = (root / "Documents" / "logs" / "rebuild_runs" / execution.rebuild_run_id / "rebuild_manifest.json").is_file()
        checks["release_bundle_exists"] = (root / "Semantic Release" / "releases" / "tree.release" / "release.json").is_file()
    if workflow_tool == "reset_database":
        checks["reset_manifest_exists"] = bool(list((root / "Documents" / "logs" / "pipeline_batches" / "resets").glob("rstman_*.json")))
    if workflow_tool == "manual_pipeline_run":
        batch_root = root / "Documents" / "logs" / "pipeline_batches"
        checks["pending_manifest_exists"] = bool(list(batch_root.glob("pbt_*/pending_pipeline_batch_manifest.json")))
        checks["final_manifest_exists"] = bool(list(batch_root.glob("pbt_*/pipeline_batch_manifest.json")))
        checks["correlation_report_exists"] = bool(list(batch_root.glob("pbt_*/correlation_report.json")))
    return checks

def _target_database_path(execution: Any) -> Path:
    target = getattr(execution, "target", None)
    if target is not None:
        return Path(target.database_path)
    if isinstance(getattr(execution, "selection", None), Mapping):
        return Path(str(execution.selection.get("target_database_path", "")))
    return Path(str(getattr(execution, "target_database_path", "")))
