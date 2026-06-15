from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from semantic_control_kernel.workflows.database_creation.final_notice.constants import _DATABASE_CREATION_STEP_FACTS
from semantic_control_kernel.workflows.explanation_context import build_workflow_explanation_context

if TYPE_CHECKING:
    from semantic_control_kernel.workflows.database_creation.shared_steps import DatabaseCreationExecution


def _created_artifacts(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    target = execution.target
    artifacts = execution.artifacts
    return {
        "artifact_root_path": target.artifact_root_path if target is not None else "",
        "database_path": target.database_path if target is not None else "",
        "semantic_release_path": target.semantic_release_path if target is not None else "",
        "default_release_export_path": str(artifacts.get("default_release_export_path") or ""),
        "default_release_path": str(artifacts.get("default_release_path") or ""),
        "projectionless_release_state_path": str(artifacts.get("projectionless_release_state_path") or ""),
        "custom_taxonomy_stage_path": _staged_component_artifact_path(execution, "taxonomy"),
    }


def _artifact_path_summary(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    paths = _created_artifacts(execution)
    paths.update({key: str(value) for key, value in execution.artifacts.items() if key.endswith("_path") and value and key not in paths})
    return paths


def _workflow_explanation_context(execution: "DatabaseCreationExecution") -> dict[str, Any]:
    artifacts = _created_artifacts(execution)
    unchanged: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    already_step_ids = set(getattr(execution, "completed_step_ids_at_run_start", ()))
    for step_id, keys in (
        ("dc_create_artifact_tree", ("artifact_root_path",)),
        ("dc_create_empty_database", ("database_path",)),
        ("dc_write_default_release", ("default_release_path",)),
        ("dc_remove_default_projections", ("projectionless_release_state_path",)),
        ("tax_stage_custom_taxonomy", ("custom_taxonomy_stage_path",)),
    ):
        for key in keys:
            value = artifacts.get(key)
            if value:
                (unchanged if step_id in already_step_ids else changed).append({"step_id": step_id, "artifact_key": key, "path": value})
    return build_workflow_explanation_context(
        execution,
        step_facts=_DATABASE_CREATION_STEP_FACTS,
        current_state_summary=execution.final_state,
        unchanged_artifacts=unchanged,
        changed_artifacts=changed,
    )


def _created_artifact_summary_sentence(
    execution: "DatabaseCreationExecution",
    *,
    include_default_release: bool = False,
    include_projectionless_state: bool = False,
    include_custom_taxonomy_stage: bool = False,
    prefix: str = "Created paths",
) -> str:
    artifacts = _created_artifacts(execution)
    entries = [("Artifact Tree path", artifacts["artifact_root_path"]), ("Corpus DB path", artifacts["database_path"])]
    if include_default_release:
        entries.append(("Default Semantic Release path", artifacts["default_release_path"]))
    if include_projectionless_state:
        entries.append(("Projectionless release state path", artifacts["projectionless_release_state_path"]))
    if include_custom_taxonomy_stage:
        entries.append(("Custom taxonomy stage path", artifacts["custom_taxonomy_stage_path"]))
    visible = [f"{label}: {value}" for label, value in entries if value]
    return f"{prefix}: " + "; ".join(visible) + "." if visible else ""


def _staged_component_artifact_path(execution: "DatabaseCreationExecution", component_kind: str) -> str:
    staged = execution.artifacts.get("staged_taxonomy_ref" if component_kind == "taxonomy" else "staged_projection_ref")
    artifact_ref = staged.get("artifact_ref") if isinstance(staged, Mapping) else None
    return str(artifact_ref.get("artifact_path") or "") if isinstance(artifact_ref, Mapping) else ""


def _already_available_sentence_part(context: Mapping[str, Any]) -> str:
    labels = [str(item.get("label") or "") for item in context.get("already_available", []) if isinstance(item, Mapping)]
    labels = [label for label in labels if label]
    return "previous workflow prerequisites" if not labels else labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]
