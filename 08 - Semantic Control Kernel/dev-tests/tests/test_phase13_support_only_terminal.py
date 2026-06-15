from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.domain.recovery import AdapterMissingCapability, RecoveryContext, SemanticExceptionHandler
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


def test_unknown_exception_creates_support_only_event_with_redacted_bundle(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_support",
            workflow_tool="database_merge_additive_only",
            failed_kernel_step="owner_call",
            target_identity={"target_hash": "support_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_support"},
        ),
        lambda: (_ for _ in ()).throw(RuntimeError("Traceback token sk-secret")),
    )

    assert result.recovery_event.payload["status"] == "support_only"
    assert result.recovery_event.payload["allowed_agent_tools"] == ["kernel_open_support_bundle"]
    assert result.recovery_event.payload["support_bundle_ref"]["redaction_profile"]["raw_payloads_included"] is False


def test_missing_capability_without_safe_recovery_has_no_mutation_options(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    result = _handler(paths).run_step(
        RecoveryContext(
            workflow_run_id="wr_missing_capability",
            workflow_tool="database_rebuild_from_artifacts",
            failed_kernel_step="corpus_builder",
            target_identity={"target_hash": "capability_target"},
            state_snapshot_identity={"state_snapshot_id": "ss_capability"},
        ),
        lambda: (_ for _ in ()).throw(
            AdapterMissingCapability(
                "pipeline_capability_missing",
                "The owner capability needed for recovery is missing.",
                technical_context={"missing_capability": True},
            )
        ),
    )

    assert result.recovery_event.payload["recovery_state"] == "support_only_unrecoverable"
    assert [option["agent_tool"] for option in result.recovery_event.payload["recovery_options"]] == ["kernel_open_support_bundle"]
    assert "invent" not in str(result.recovery_event.payload["recovery_options"]).lower()
