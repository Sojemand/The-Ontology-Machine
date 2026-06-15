from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from semantic_control_kernel.repository.paths import path_hash, stable_hash
from semantic_control_kernel.types.batches import PipelineInputFile, PipelineRunBlocker, PipelineRunTarget
from semantic_control_kernel.types.adapter_results import AdapterCallResult
from semantic_control_kernel.workflows.pipeline_run.input_inventory import input_set_hash


def pipeline_confirmation(
    target: PipelineRunTarget,
    input_files: list[PipelineInputFile],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "confirmed",
        "confirmation_scope": "manual_pipeline_run",
        "target_identity": target.target_identity,
        "state_snapshot_id": target.state_snapshot_id,
        "input_set_hash": input_set_hash(input_files),
        "confirmation_receipt": dict(receipt),
    }


def orchestrator_ui_state(target: PipelineRunTarget) -> dict[str, Any]:
    return {
        "input_folder": target.input_path,
        "artifact_folder": target.artifact_root_path,
        "semantic_release_path": "",
        "corpus_output_folder": target.corpus_path,
        "selected_corpus_db_path": target.database_path,
        "semantic_release_mode": "database_default",
        "mode": "batch",
    }


def input_confirmation_identity(target: PipelineRunTarget, input_files: list[PipelineInputFile]) -> dict[str, Any]:
    return {
        **interaction_target_identity(target),
        "input_path_hash": path_hash(target.input_path),
        "workflow_run_id": target.workflow_run_id,
    }


def input_confirmation_request_id(target: PipelineRunTarget, input_files: list[PipelineInputFile]) -> str:
    return f"manual_pipeline_run.input_presence:{target.workflow_run_id}:{target.database_path_hash}:{input_set_hash(input_files)}"


def input_state_snapshot_id(target: PipelineRunTarget, input_files: list[PipelineInputFile]) -> str:
    return stable_hash(f"{target.state_snapshot_id}:{input_set_hash(input_files)}")


def restore_confirmation_identity(target: PipelineRunTarget, scope: str) -> dict[str, Any]:
    return {
        **interaction_target_identity(target),
        "input_path_hash": path_hash(target.input_path),
        "workflow_run_id": target.workflow_run_id,
    }


def interaction_target_identity(target: PipelineRunTarget) -> dict[str, Any]:
    return {key: value for key, value in target.target_identity.items() if key != "state_snapshot_id"}


def manual_placeholder_identity(workflow_run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "state.target_identity.v1",
        "artifact_root_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:manual_pipeline_artifact_root')}",
        "database_path_hash": f"pending:{stable_hash(f'{workflow_run_id}:manual_pipeline_database')}",
        "target_hash": stable_hash(f"{workflow_run_id}:manual_pipeline_target"),
        "lock_scope": "manual_pipeline_run",
        "workflow_run_id": workflow_run_id,
        "created_from": "kernel.manual_pipeline_target_collection.v1",
    }


def interaction_snapshot_id(workflow_run_id: str, interaction_function: str) -> str:
    return stable_hash(f"{workflow_run_id}:{interaction_function}")


def existing_corpus_databases(corpus_dir: Path) -> tuple[Path, ...]:
    if not corpus_dir.is_dir():
        return ()
    return tuple(
        path.resolve(strict=False)
        for path in sorted(corpus_dir.iterdir(), key=lambda item: item.name.casefold())
        if path.is_file() and path.suffix.casefold() == ".db"
    )


def adapter_output(result: object) -> dict[str, Any]:
    if isinstance(result, AdapterCallResult):
        payload = result.to_dict()
        output = payload.get("output_refs")
        return dict(output) if isinstance(output, Mapping) else {}
    return dict(result) if isinstance(result, Mapping) else {}


def prefilled_values_for(interaction_function: str, progress: Any) -> dict[str, Any]:
    if interaction_function == "choose_artifact_root_folder" and getattr(progress, "artifact_root", None):
        return {"path_value": progress.artifact_root}
    return {}


def input_blocker(summary: str) -> PipelineRunBlocker:
    return PipelineRunBlocker(
        blocker_code="input_missing",
        step_id="manual_pipeline_collect_interaction",
        function_or_route="manual_pipeline_run",
        recovery_state_class="expired_pending_interaction",
        user_visible_summary=summary,
    )


def clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def clean_path(value: object) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
        if not text:
            return None
    return str(Path(text).resolve(strict=False))
