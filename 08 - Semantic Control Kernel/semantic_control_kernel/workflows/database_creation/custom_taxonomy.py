from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from semantic_control_kernel.policy.runtime_locale import DEFAULT_CONTROL_LOCALE
from semantic_control_kernel.types.database_creation import DatabaseCreationBlocker, DatabaseCreationTarget
from semantic_control_kernel.workflows.database_creation.llm_path_helpers import (
    AnalysisReportOutcome,
    run_sample_proposal_update_path,
)
from semantic_control_kernel.workflows.database_creation.shared_steps import (
    validate_selected_sample_refs,
)
from semantic_control_kernel.workflows.llm_calls.update_state_builders import (
    create_taxonomy_update_state,
)


def validate_taxonomy_samples(
    *,
    target: DatabaseCreationTarget | None,
    sample_refs: Sequence[Mapping[str, Any]],
) -> DatabaseCreationBlocker | None:
    return validate_selected_sample_refs(
        target=target,
        sample_refs=sample_refs,
        step_id="tax_require_samples",
        sample_subject="taxonomy",
    )


def run_taxonomy_llm_path(
    llm_port: Any,
    *,
    workflow_run_id: str,
    artifact_root: str | Path,
    sample_refs: Sequence[Mapping[str, Any]],
    target: DatabaseCreationTarget | None = None,
    runtime_settings: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, DatabaseCreationBlocker | None, list[str], list[tuple[AnalysisReportOutcome, str]]]:
    return run_sample_proposal_update_path(
        llm_port,
        unavailable_step_id="tax_analyze_samples",
        unavailable_summary="Phase 8 LLM function port is unavailable for custom taxonomy creation.",
        workflow_run_id=workflow_run_id,
        analysis_suffix="taxonomy",
        artifact_root=artifact_root,
        sample_refs=sample_refs,
        target=target,
        runtime_settings=runtime_settings,
        sample_step_id="tax_analyze_samples",
        proposal_step_id="tax_create_proposal",
        update_step_id="tax_build_update_state",
        proposal_function="create_taxonomy_to_sample_analyses",
        proposal_input=lambda sample_output: {"sample_analyses": sample_output},
        update_function="create_taxonomy_update_state",
        update_state=lambda proposal_output, analysis_run_id, root: create_taxonomy_update_state(
            proposal_output,
            analysis_run_id=analysis_run_id,
            artifact_root=root,
            real_taxonomy_proof={"runtime_locale": DEFAULT_CONTROL_LOCALE},
        ),
    )
