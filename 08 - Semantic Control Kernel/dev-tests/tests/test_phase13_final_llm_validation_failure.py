from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import LLMFinalValidationFailure, RecoveryContext, SemanticExceptionHandler
from semantic_control_kernel.domain.recovery.retry_resume import RetryResumeService
from semantic_control_kernel.domain.recovery.support_bundle import SupportBundleService
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.repository.support_bundles import SupportBundleStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService


def _handler(paths: StatePaths) -> SemanticExceptionHandler:
    return SemanticExceptionHandler(
        recovery_event_store=RecoveryEventStore(paths),
        mirror_event_service=KernelMirrorEventService(MirrorEventStore(paths)),
        support_bundle_service=SupportBundleService(SupportBundleStore(paths)),
    )


def test_final_llm_failure_safe_retry_and_no_json_repair_request(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_llm",
            workflow_tool="create_custom_taxonomy_path",
            failed_kernel_step="create_taxonomy_to_sample_analyses",
            target_identity={"target_hash": "llm_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_llm"},
        ),
        lambda: (_ for _ in ()).throw(
            LLMFinalValidationFailure(
                "final_llm_validation_failure",
                "The LLM failed final Kernel validation.",
                safe_resume_available=True,
            )
        ),
    )
    event = result.recovery_event.payload
    retry_option = next(option for option in event["recovery_options"] if option["agent_tool"] == "kernel_retry_recoverable_workflow")
    retry = RetryResumeService(RecoveryEventStore(paths)).retry(
        event,
        retry_option["recovery_id"],
        {
            "failed_call_isolated": True,
            "input_hashes_match": True,
            "safe_resume_point": True,
            "target_identity_matches": True,
            "workflow_run_id": "wr_llm",
        },
    )

    assert retry["result_status"] == "applied"
    assert "repair" not in str(result.mirror_event).lower()
    assert event["support_bundle_ref"]["safe_summary"] == "The LLM failed final Kernel validation."


def test_final_llm_failure_unsafe_retry_blocks_to_cancel_resume_or_support(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_llm_unsafe",
            workflow_tool="create_custom_projection_path",
            failed_kernel_step="create_projections_to_sample_analyses",
            target_identity={"target_hash": "llm_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_llm"},
        ),
        lambda: (_ for _ in ()).throw(
            LLMFinalValidationFailure("final_llm_validation_failure", "The LLM failed final Kernel validation.")
        ),
    )

    assert "kernel_retry_recoverable_workflow" not in result.recovery_event.payload["allowed_agent_tools"]
    assert "kernel_open_support_bundle" in result.recovery_event.payload["allowed_agent_tools"]
    assert "json" not in result.recovery_event.payload["user_visible_cause"].lower()


def test_final_llm_retry_rejects_unbound_recovery_ids(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_llm_bound",
            workflow_tool="create_custom_taxonomy_path",
            failed_kernel_step="create_taxonomy_to_sample_analyses",
            target_identity={"target_hash": "llm_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_llm"},
        ),
        lambda: (_ for _ in ()).throw(
            LLMFinalValidationFailure(
                "final_llm_validation_failure",
                "The LLM failed final Kernel validation.",
                safe_resume_available=True,
            )
        ),
    )
    rejected = RetryResumeService(RecoveryEventStore(paths)).retry(
        result.recovery_event.payload,
        "missing_recovery_id",
        {
            "failed_call_isolated": True,
            "input_hashes_match": True,
            "safe_resume_point": True,
            "target_identity_matches": True,
            "workflow_run_id": "wr_llm_bound",
        },
    )

    assert rejected["result_status"] == "rejected"
    assert rejected["progress_event_ref"] is None
