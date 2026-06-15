from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.domain.recovery.staged_work_archive import StagedWorkArchiveService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.repository.event_store import MirrorEventStore
from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.paths import utc_iso
from semantic_control_kernel.repository.recovery_events import RecoveryEventStore
from semantic_control_kernel.services.kernel_mirror_event_service import KernelMirrorEventService
from semantic_control_kernel.types.enums import MirrorEventType, MirrorSeverity, RecoveryStateClass
from semantic_control_kernel.types.recovery import RECOVERY_EVENT_SCHEMA_VERSION

from test_phase13_database_artifact_rebind import _event as _binding_event


def _archive_event(paths: StatePaths, *, destructive_scope: bool = False):
    expires = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    options = RecoveryOptionService().create_options(
        recovery_event_id="rev_archive",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity={"target_hash": "archive_target"},
        state_snapshot_identity={"state_snapshot_id": "ss_archive"},
        expires_at=expires,
        safe_tools=("kernel_discard_or_archive_staged_work",),
        evidence={"destructive_scope": destructive_scope},
    )
    mirror = KernelMirrorEventService(MirrorEventStore(paths)).create_mirror_event(
        event_type=MirrorEventType.RECOVERY_STATE.value,
        severity=MirrorSeverity.RECOVERABLE_ERROR.value,
        user_visible_summary="Archive staged work.",
        current_state_summary="Archive recovery.",
        recovery_options=[option.to_dict() for option in options],
        allowed_agent_tools=("kernel_discard_or_archive_staged_work",),
        tool_availability_expires_at=expires,
    )
    return RecoveryEventStore(paths).put_recovery_event(
        {
            "allowed_agent_tools": ["kernel_discard_or_archive_staged_work"],
            "blocked_functions": ["manual_pipeline_run"],
            "cause_code": "target_identity_changed",
            "created_at": utc_iso(),
            "detected_by": "test",
            "expires_at": expires,
            "failed_kernel_step": "archive_step",
            "mirror_event_id": mirror.payload["mirror_event_id"],
            "recovery_event_id": "rev_archive",
            "recovery_options": [option.to_dict() for option in options],
            "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
            "schema_version": RECOVERY_EVENT_SCHEMA_VERSION,
            "state_snapshot_identity": {"state_snapshot_id": "ss_archive"},
            "status": "active",
            "superseded_by": None,
            "support_bundle_ref": None,
            "target_identity": {"target_hash": "archive_target"},
            "user_visible_cause": "Target changed with staged work.",
            "workflow_run_id": "wr_archive",
            "workflow_tool": "manual_pipeline_run",
        }
    ), options[0]


def test_half_built_db_incomplete_release_failed_merge_and_llm_folders_are_archived(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    event, option = _archive_event(paths)
    service = StagedWorkArchiveService(paths, RecoveryEventStore(paths))

    refs = [
        {"kind": "half_built_database", "ref": "state/work/half_db"},
        {"kind": "incomplete_semantic_release", "ref": "state/work/release"},
        {"kind": "failed_merge_target", "ref": "state/work/merge"},
        {"kind": "failed_llm_analysis_folder", "ref": "state/work/llm"},
    ]
    result = service.archive_or_discard(event.payload, option.payload["recovery_id"], "staged_bundle", original_refs=refs)
    manifest = json.loads((paths.state_root / result["archive_ref"]["archive_path"]).read_text(encoding="utf-8"))

    assert result["result_status"] == "applied"
    assert (paths.state_root / result["archive_ref"]["archive_path"]).is_file()
    assert manifest["affected_recovery_event_ids"] == [event.payload["recovery_event_id"]]
    assert manifest["affected_workflow_run_ids"] == [event.payload["workflow_run_id"]]
    assert result["receipt"].payload["written_refs"]


def test_destructive_discard_requires_bound_scope_and_rejects_wrong_recovery_tool(tmp_path: Path) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    wrong_event, wrong_option = _binding_event(paths)
    event, option = _archive_event(paths, destructive_scope=True)
    service = StagedWorkArchiveService(paths, RecoveryEventStore(paths))

    wrong_tool = service.archive_or_discard(
        wrong_event.payload,
        wrong_option.payload["recovery_id"],
        "active-production-data",
        destructive=True,
        confirmation_ref={"confirmation_receipt_id": "cfr_wrong"},
        scope_is_explicit=True,
    )
    rejected = service.archive_or_discard(
        event.payload,
        option.payload["recovery_id"],
        "active-production-data",
        destructive=True,
        confirmation_ref={"confirmation_receipt_id": "cfr_missing_scope"},
    )
    applied = service.archive_or_discard(
        event.payload,
        option.payload["recovery_id"],
        "explicit-staged-scope",
        destructive=True,
        confirmation_ref={"confirmation_receipt_id": "cfr_archive"},
        scope_is_explicit=True,
    )

    assert wrong_tool["result_status"] == "rejected"
    assert rejected["result_status"] == "rejected"
    assert applied["discard_receipt_id"] == applied["receipt"].payload["recovery_receipt_id"]
    assert applied["receipt"].payload["user_confirmation_refs"] == [{"confirmation_receipt_id": "cfr_archive"}]
