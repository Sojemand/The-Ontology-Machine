"""Run and reset actions for the orchestrator contract surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..workspace_domain.adapter import owner_response
from .pipeline_owner_refs import mapping_field, pipeline_owner_output_refs, run_target_identity_proof
from .workflow_snapshot import _snapshot_file_writer


def run_action(
    ui_state_data: dict,
    *,
    engine_cls,
    ui_state_cls,
    snapshot_path: str = "",
    request_payload: dict[str, Any] | None = None,
    owner_result: bool = False,
) -> dict:
    ui_state = ui_state_cls.from_dict(ui_state_data)
    snapshot_callback = _snapshot_file_writer(snapshot_path, artifact_root=getattr(ui_state, "artifact_folder", ""))
    engine = engine_cls(snapshot_callback=snapshot_callback) if snapshot_callback else engine_cls()
    try:
        owner_input_hashes = _owner_input_hashes(request_payload)
        summary = (
            engine.run(ui_state)
            if owner_input_hashes is None
            else engine.run(ui_state, owner_input_hashes=owner_input_hashes)
        )
        output_refs = pipeline_owner_output_refs(
            engine=engine,
            ui_state=ui_state,
            summary=summary,
            request_payload=request_payload or {},
        ) if owner_result else {}
    finally:
        engine.close()
    result = {
        "status": "ok",
        "total": summary.total,
        "success": summary.success,
        "errors": summary.errors,
        "needs_review": summary.needs_review,
        "retries": summary.retries,
    }
    if not owner_result:
        return result
    target_identity = mapping_field(request_payload or {}, "target_identity")
    proof = run_target_identity_proof(ui_state, request_payload or {}, target_identity)
    return owner_response(
        owner_action="run",
        capability="orchestrator_pipeline_run",
        target_identity=target_identity,
        output_refs=output_refs,
        target_identity_proof=proof,
        receipt_fields={
            "owner_module": "00 - Orchestrator",
            "owner_action": "run",
            "orchestrator_run_id": output_refs.get("owner_run_refs", {}).get("orchestrator_run_id", ""),
            "pipeline_batch_id": str((request_payload or {}).get("pipeline_batch_id") or ""),
        },
        summary="Pipeline run completed.",
    )


def reset_action(
    ui_state_data: dict,
    *,
    engine_cls,
    ui_state_cls,
    request_payload: dict[str, Any] | None = None,
    owner_result: bool = False,
) -> dict:
    ui_state = ui_state_cls.from_dict(ui_state_data)
    engine = engine_cls()
    try:
        summary = engine.reset_run_history(ui_state)
    finally:
        engine.close()
    result = {
        "status": "ok",
        "cleared_records": summary.cleared_records,
        "restored_sources": summary.restored_sources,
        "renamed_conflicts": summary.renamed_conflicts,
        "removed_targets": summary.removed_targets,
    }
    if not owner_result:
        return result
    proof = run_target_identity_proof(ui_state, request_payload or {}, mapping_field(request_payload or {}, "target_identity"))
    return {**result, "output_refs": dict(proof), "target_identity_proof": proof}


def reset_pipeline_logs_action(
    ui_state_data: dict,
    *,
    engine_cls,
    ui_state_cls,
    reset_logging_files,
) -> dict:
    engine = engine_cls()
    try:
        summary = engine.reset_pipeline_logs(ui_state_cls.from_dict(ui_state_data))
        summary.removed_log_targets = _relative_targets(
            reset_logging_files(engine._project_state_dir),
            root=engine._root,
        )
    finally:
        engine.close()
    return {
        "status": "ok",
        "cleared_records": summary.cleared_records,
        "removed_pipeline_targets": list(summary.removed_pipeline_targets),
        "removed_log_targets": list(summary.removed_log_targets),
    }


def _owner_input_hashes(request_payload: dict[str, Any] | None) -> set[str] | None:
    payload = request_payload or {}
    if "input_files" not in payload:
        return None
    input_files = payload.get("input_files")
    if not isinstance(input_files, list):
        return set()
    return {
        str(item.get("content_hash") or "").strip()
        for item in input_files
        if isinstance(item, dict) and str(item.get("content_hash") or "").strip()
    }


def _relative_targets(paths: tuple[Path, ...], *, root: Path) -> tuple[str, ...]:
    values: list[str] = []
    for path in paths:
        try:
            values.append(path.relative_to(root).as_posix())
        except ValueError:
            values.append(str(path))
    return tuple(values)
