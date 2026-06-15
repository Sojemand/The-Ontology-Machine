from __future__ import annotations

from pathlib import Path

import pytest

from semantic_control_kernel.domain.recovery import (
    BrokenDatabaseArtifactBinding,
    ExpiredPendingInteraction,
    LLMFinalValidationFailure,
    MergeCollisionUnresolved,
    MissingManifestOrOriginals,
    PartialPipelineRunDetected,
    RecoveryContext,
    SemanticExceptionHandler,
    SemanticReleaseIncomplete,
    StaleLockDetected,
    TargetIdentityChanged,
)
from semantic_control_kernel.domain.recovery.semantic_exception_handler import UnexpectedKernelException
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.interaction_store import InteractionRequestStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.agent_tool_invocation_service import AgentToolInvocationService
from semantic_control_kernel.services.agent_tool_workflow_dispatch import _result_from_execution
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import ProgressStatus, RecoveryStateClass


EXCEPTIONS = (
    (StaleLockDetected, RecoveryStateClass.STALE_LOCK.value),
    (TargetIdentityChanged, RecoveryStateClass.TARGET_IDENTITY_CHANGED.value),
    (BrokenDatabaseArtifactBinding, RecoveryStateClass.BROKEN_DATABASE_ARTIFACT_BINDING.value),
    (SemanticReleaseIncomplete, RecoveryStateClass.SEMANTIC_RELEASE_INCOMPLETE_STAGED.value),
    (PartialPipelineRunDetected, RecoveryStateClass.PARTIAL_PIPELINE_RUN.value),
    (MergeCollisionUnresolved, RecoveryStateClass.UNRESOLVED_MERGE_COLLISION.value),
    (MissingManifestOrOriginals, RecoveryStateClass.MISSING_MANIFEST_OR_ORIGINALS.value),
    (LLMFinalValidationFailure, RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value),
    (ExpiredPendingInteraction, RecoveryStateClass.EXPIRED_PENDING_INTERACTION.value),
    (UnexpectedKernelException, RecoveryStateClass.SUPPORT_ONLY_UNRECOVERABLE.value),
)


def _handler(tmp_path: Path) -> SemanticExceptionHandler:
    paths = StatePaths.from_state_root(tmp_path / "state")
    return SemanticExceptionHandler(
        recovery_event_store=RecoveryEventStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        support_bundle_service=SupportBundleService(SupportBundleStore(paths)),
    )


def _context() -> RecoveryContext:
    return RecoveryContext(
        workflow_run_id="wr_phase13",
        workflow_tool="manual_pipeline_run",
        failed_kernel_step="phase13_step",
        target_identity={"target_hash": "target_phase13"},
        state_snapshot_identity={"state_snapshot_id": "ss_phase13"},
        blocked_functions=("manual_pipeline_run",),
    )


@pytest.mark.parametrize(("exc_type", "expected_state"), EXCEPTIONS)
def test_semantic_exception_handler_classifies_every_input_class(tmp_path: Path, exc_type, expected_state: str) -> None:
    result = _handler(tmp_path).run_step(
        _context(),
        lambda: (_ for _ in ()).throw(
            exc_type(
                cause_code=f"{expected_state}_cause",
                user_visible_cause=f"{expected_state} blocked.",
                blocked_functions=("manual_pipeline_run",),
                safe_resume_available=expected_state == RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value,
            )
        ),
    )

    assert result.recovery_event.payload["recovery_state"] == expected_state
    assert result.recovery_event.payload["state_snapshot_identity"] == {"state_snapshot_id": "ss_phase13"}
    assert result.recovery_event.payload["target_identity"] == {"target_hash": "target_phase13"}
    assert result.mirror_event["mirror_source"] == "kernel"
    assert result.mirror_event["is_kernel_auto_call"] is True
    assert result.progress_event.payload["status"] in {ProgressStatus.BLOCKED.value, ProgressStatus.FAILED.value}


def test_unexpected_python_exception_becomes_redacted_support_only(tmp_path: Path) -> None:
    result = _handler(tmp_path).run_step(_context(), lambda: (_ for _ in ()).throw(RuntimeError("secret token sk-test")))

    assert result.recovery_event.payload["recovery_state"] == "support_only_unrecoverable"
    support_ref = result.recovery_event.payload["support_bundle_ref"]
    assert support_ref["safe_summary"]
    assert "sk-test" not in support_ref["safe_summary"]
    assert result.recovery_event.payload["allowed_agent_tools"] == ["kernel_open_support_bundle"]


def test_manual_pipeline_agent_dispatch_opens_interaction_without_recovery_event(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = AgentToolInvocationService(state_paths=paths).invoke("manual_pipeline_run", {}, {}).to_dict()

    assert result["status"] == "ok"
    assert result["effect"] == "workflow_started"
    assert result["final_state"] == "awaiting_manual_pipeline_interaction"
    assert result["user_visible_summary"] == "Choose the Artifact Tree whose Input folder should be ingested into its active Corpus database."

    workflow_run_id = result["workflow_run_id"]
    pending = InteractionRequestStore(paths).list_pending_interactions_for_workflow(workflow_run_id)
    assert len(pending) == 1
    request = pending[0].payload
    assert request["function_or_route"] == "manual_pipeline_run"
    assert request["interaction_function"] == "choose_artifact_root_folder"
    assert request["response_shape"] == "path_value"

    active_runs = list(WorkflowRunStore(paths).list_active_runs())
    assert len(active_runs) == 1
    run = active_runs[0].to_dict()
    assert run["workflow_run_id"] == workflow_run_id
    assert run["workflow_tool"] == "manual_pipeline_run"
    assert run["status"] == "waiting"
    assert run["resume_state_ref"].startswith("pending_interactions/active/")
    assert not list(paths.events_recovery_dir.glob("*/recovery_event.json"))


def test_blocked_dispatch_with_llm_support_ref_does_not_crash_on_empty_metadata(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    attempt_ref = {
        "attempt_index": 1,
        "prompt_snapshot_ref": "tax_sa/wr_tax/a/1/prompt.json",
        "validation_report_ref": "tax_sa/wr_tax/a/1/val.json",
    }
    execution = {
        "workflow_run_id": "wr_tax",
        "workflow_tool": "empty_database_custom_taxonomy_no_projections",
        "status": "blocked",
        "final_state": "no_semantic_release",
        "blocked_step_id": "tax_create_proposal",
        "blocker": {
            "step_id": "tax_create_proposal",
            "function_or_route": "create_taxonomy_to_sample_analyses",
            "blocker_code": "final_llm_validation_failure",
            "recovery_state_class": "final_llm_validation_failure",
            "user_visible_summary": "The LLM failed final Kernel validation.",
            "diagnostics": [
                {
                    "schema_version": "kernel.llm_final_error.v1",
                    "error_code": "llm_validation_exhausted",
                    "support_bundle_ref": {
                        "schema_version": "kernel.support_bundle_ref.v1",
                        "support_bundle_id": "spt_existing",
                        "support_bundle_path": "support/bundles/spt_existing/support_bundle_manifest.json",
                        "recovery_event_id": "",
                        "safe_summary": "Existing LLM failure bundle.",
                        "included_refs": [attempt_ref],
                        "redaction_profile": {},
                    },
                    "failed_attempt_artifact_refs": [attempt_ref],
                    "validation_error_summary": "The LLM failed final Kernel validation.",
                }
            ],
        },
    }

    result = _result_from_execution(
        "empty_database_custom_taxonomy_no_projections",
        execution,
        state_paths=paths,
    ).to_dict()

    assert result["status"] == "blocked"
    assert result["mirror_event"]["event_type"] == "llm_validation_failed_final"
    assert result["recovery_event"]["recovery_state"] == RecoveryStateClass.FINAL_LLM_VALIDATION_FAILURE.value
