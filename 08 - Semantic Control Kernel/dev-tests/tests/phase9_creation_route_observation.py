from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.repository.attach_state_store import AttachStateStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.types.database_creation import CANONICAL_ARTIFACT_FOLDERS


def freeze_observation(execution, semantic, llm, target, tmp_path: Path) -> dict[str, object]:
    root = Path(target.artifact_root_path)
    artifact_files = _artifact_files(root)
    return {
        "artifact_files": artifact_files,
        "artifact_json_contracts": _artifact_json_contracts(root, artifact_files),
        "attach_state_present": _has_attach_state(tmp_path, target.target_identity),
        "completed_step_ids": list(execution.completed_step_ids),
        "execution_artifact_keys": sorted(execution.artifacts.keys()),
        "final_state": execution.final_state,
        "llm_calls": [name for name, _payload in llm.calls],
        "llm_progress_completed": list(_completed_llm_progress_steps(execution.progress_events)),
        "mirror_event_types": [event.get("event_type") for event in execution.mirror_events],
        "operation_log": list(execution.operation_log),
        "resume_tools": list(_resume_tools(execution)),
        "semantic_calls": list(semantic.calls),
        "status": execution.status,
        "target": {
            "artifact_root_name": target.artifact_root_name,
            "database_name": target.database_name,
        },
        "workflow_progress_completed": list(_workflow_step_completions(execution.progress_events)),
        "workflow_progress_started": list(_workflow_step_starts(execution.progress_events)),
        "workflow_run_id": execution.workflow_run_id,
        "workflow_tool": execution.workflow_tool,
    }


def canonical_artifact_folders(target) -> tuple[str, ...]:
    root = Path(target.artifact_root_path)
    return tuple(folder for folder in CANONICAL_ARTIFACT_FOLDERS if (root / folder).is_dir())


def _resume_tools(execution) -> tuple[str, ...]:
    if execution.resume_context is None:
        return ()
    return tuple(execution.resume_context.allowed_continuation_workflow_tools)


def _artifact_files(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _artifact_json_contracts(root: Path, artifact_files: list[str]) -> dict[str, object]:
    contracts = {}
    for relative_path in artifact_files:
        path = root / relative_path
        if path.suffix == ".json":
            contracts[relative_path] = _json_contract_summary(
                relative_path,
                json.loads(path.read_text(encoding="utf-8")),
            )
    return contracts


def _json_contract_summary(relative_path: str, payload: dict[str, object]) -> dict[str, object]:
    if relative_path.endswith("/release.json"):
        taxonomy_ref = payload.get("taxonomy_ref") if isinstance(payload.get("taxonomy_ref"), dict) else {}
        projection_refs = payload.get("projection_refs") if isinstance(payload.get("projection_refs"), list) else []
        return {
            "projection_count": len(projection_refs),
            "projection_ids": [item.get("projection_id") for item in projection_refs if isinstance(item, dict)],
            "release_fingerprint": payload.get("release_fingerprint"),
            "release_id": payload.get("release_id"),
            "release_version": payload.get("release_version"),
            "runtime_locale": payload.get("runtime_locale"),
            "taxonomy_fingerprint": taxonomy_ref.get("taxonomy_fingerprint"),
            "taxonomy_id": taxonomy_ref.get("taxonomy_id"),
        }
    if relative_path.endswith("/projectionless_release_state.json"):
        projectionless_ref = payload.get("projectionless_release_ref")
        if not isinstance(projectionless_ref, dict):
            projectionless_ref = {}
        return {
            "completeness_state": payload.get("completeness_state"),
            "missing_component_type": payload.get("missing_component_type"),
            "projectionless_projection_count": len(projectionless_ref.get("projection_refs") or []),
            "projectionless_release_id": projectionless_ref.get("release_id"),
            "remaining_projection_count": len(payload.get("remaining_projection_refs") or []),
            "removed_projection_count": len(payload.get("removed_projection_refs") or []),
            "schema_version": payload.get("schema_version"),
            "workflow_tool": payload.get("workflow_tool"),
        }
    if relative_path.endswith("/incomplete_semantic_release.json"):
        resume = payload.get("resume_context") if isinstance(payload.get("resume_context"), dict) else {}
        staged_refs = resume.get("staged_component_refs") if isinstance(resume.get("staged_component_refs"), list) else []
        return {
            "allowed_continuation_workflow_tools": resume.get("allowed_continuation_workflow_tools", []),
            "has_projectionless_release_ref": bool(payload.get("projectionless_release_ref")),
            "has_projectionless_release_state_ref": bool(payload.get("projectionless_release_state_ref")),
            "next_step_id": resume.get("next_step_id"),
            "schema_version": payload.get("schema_version"),
            "staged_component_kinds": [item.get("component_kind") for item in staged_refs if isinstance(item, dict)],
            "state": payload.get("state"),
            "workflow_tool": resume.get("workflow_tool"),
        }
    if relative_path.endswith("/tax_update.json"):
        taxonomy_core = payload.get("taxonomy_core") if isinstance(payload.get("taxonomy_core"), dict) else {}
        field_codes = taxonomy_core.get("field_codes") if isinstance(taxonomy_core.get("field_codes"), list) else []
        return {
            "field_codes": [item.get("code") for item in field_codes if isinstance(item, dict)],
            "runtime_locale": payload.get("runtime_locale"),
            "sample_ids": payload.get("sample_ids"),
            "schema_version": payload.get("schema_version"),
            "taxonomy_core_keys": sorted(taxonomy_core.keys()),
        }
    if relative_path.endswith("/proj_update.json"):
        taxonomy_ref = payload.get("taxonomy_ref") if isinstance(payload.get("taxonomy_ref"), dict) else {}
        precursors = payload.get("projection_precursors") if isinstance(payload.get("projection_precursors"), list) else []
        return {
            "projection_count": len(precursors),
            "projection_ids": [item.get("projection_id") for item in precursors if isinstance(item, dict)],
            "runtime_locale": payload.get("runtime_locale"),
            "sample_ids": payload.get("sample_ids"),
            "schema_version": payload.get("schema_version"),
            "taxonomy_id": taxonomy_ref.get("taxonomy_id"),
        }
    return {"json_keys": sorted(payload.keys())}


def _workflow_step_starts(progress_events) -> tuple[str, ...]:
    return tuple(
        event["step_id"]
        for event in progress_events
        if event.get("event_type") == "workflow_step" and event.get("status") == "step_started"
    )


def _workflow_step_completions(progress_events) -> tuple[str, ...]:
    return tuple(
        event["step_id"]
        for event in progress_events
        if event.get("event_type") == "workflow_step" and event.get("status") in {"step_completed", "completed"}
    )


def _completed_llm_progress_steps(progress_events) -> tuple[str, ...]:
    return tuple(
        event["step_id"]
        for event in progress_events
        if event.get("event_type") == "llm_step" and event.get("status") == "completed"
    )


def _has_attach_state(tmp_path: Path, target_identity) -> bool:
    state_paths = StatePaths.from_state_root(tmp_path / "state")
    return AttachStateStore(state_paths).get_attach_state_for_database(target_identity) is not None
