from __future__ import annotations

import pytest

from semantic_control_kernel.domain.recovery.recovery_options import RecoveryOptionService
from semantic_control_kernel.policy.recovery_policy import RecoveryPolicy
from semantic_control_kernel.surface.event_scoped_tools import EVENT_SCOPED_RECOVERY_TOOL_NAMES
from semantic_control_kernel.types.enums import MirrorEventType, RecoveryStateClass
from semantic_control_kernel.validation.contract_validation import KernelContractError, UnknownFieldError
from semantic_control_kernel.validation.recovery_validation import (
    RECOVERY_TOOL_INPUT_FIELDS,
    RECOVERY_TOOL_OUTPUT_FIELDS,
    assert_recovery_mirror_event,
    validate_recovery_event,
    validate_recovery_tool_input,
    validate_recovery_tool_output,
)


def _value_for(field: str):
    if field == "schema_version":
        return "kernel.phase13.tool_contract.v1"
    if field == "support_bundle_ref":
        return {
            "schema_version": "kernel.support_bundle_ref.v1",
            "support_bundle_id": "spt_schema_probe",
            "support_bundle_path": "support/bundles/spt_schema_probe/support_bundle_manifest.json",
            "created_at": "2026-05-07T00:00:00Z",
            "category": "support_only_unrecoverable",
            "workflow_run_id": "wr_schema_probe",
            "recovery_event_id": "rev_schema_probe",
            "safe_summary": "Schema probe support bundle.",
            "included_refs": [],
            "redaction_profile": {
                "profile_id": "support_safe_v1",
                "raw_payloads_included": False,
                "path_policy": "module_relative_or_hashed",
                "secret_field_names": [],
            },
        }
    if field == "redaction_profile":
        return {
            "profile_id": "support_safe_v1",
            "raw_payloads_included": False,
            "path_policy": "module_relative_or_hashed",
            "secret_field_names": [],
        }
    return f"{field}_id"


def test_every_recovery_tool_has_closed_input_and_output_schema() -> None:
    assert set(RECOVERY_TOOL_INPUT_FIELDS) == set(EVENT_SCOPED_RECOVERY_TOOL_NAMES)
    assert set(RECOVERY_TOOL_OUTPUT_FIELDS) == set(EVENT_SCOPED_RECOVERY_TOOL_NAMES)

    for tool_name, fields in RECOVERY_TOOL_INPUT_FIELDS.items():
        validate_recovery_tool_input(tool_name, {field: _value_for(field) for field in fields})
    for tool_name, fields in RECOVERY_TOOL_OUTPUT_FIELDS.items():
        validate_recovery_tool_output(tool_name, {field: _value_for(field) for field in fields})


@pytest.mark.parametrize("forbidden", ["raw_database_path", "json_patch", "collision_decision", "llm_output_text", "file_list"])
def test_recovery_tool_inputs_reject_agent_authored_domain_payloads(forbidden: str) -> None:
    payload = {field: _value_for(field) for field in RECOVERY_TOOL_INPUT_FIELDS["kernel_apply_recovery_option"]}
    payload[forbidden] = "agent-authored-value"

    with pytest.raises(UnknownFieldError):
        validate_recovery_tool_input("kernel_apply_recovery_option", payload)


def test_mismatched_ids_are_authorization_not_schema_payloads() -> None:
    payload = {field: _value_for(field) for field in RECOVERY_TOOL_INPUT_FIELDS["kernel_retry_recoverable_workflow"]}

    validate_recovery_tool_input("kernel_retry_recoverable_workflow", payload)
    assert "workflow_run_id" in payload


def test_recovery_event_rejects_tools_or_options_that_are_not_bound_to_the_same_event_truth() -> None:
    expires_at = RecoveryPolicy().expires_at(RecoveryStateClass.TARGET_IDENTITY_CHANGED.value)
    option = RecoveryOptionService().create_options(
        recovery_event_id="rev_event_truth",
        recovery_state=RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        target_identity={"target_hash": "event_truth"},
        state_snapshot_identity={"state_snapshot_id": "ss_event_truth"},
        expires_at=expires_at,
        safe_tools=("kernel_open_recovery_dialog",),
    )[0].to_dict()
    bad_option = dict(option)
    bad_option["recovery_event_id"] = "rev_other"
    bad_option["target_identity"] = {"target_hash": "other_target"}
    payload = {
        "schema_version": "kernel.recovery_event.v1",
        "recovery_event_id": "rev_event_truth",
        "recovery_state": RecoveryStateClass.TARGET_IDENTITY_CHANGED.value,
        "workflow_run_id": "wr_event_truth",
        "workflow_tool": "manual_pipeline_run",
        "failed_kernel_step": "step",
        "detected_by": "test",
        "target_identity": {"target_hash": "event_truth"},
        "state_snapshot_identity": {"state_snapshot_id": "ss_event_truth"},
        "cause_code": "target_identity_changed",
        "user_visible_cause": "Target changed.",
        "blocked_functions": ["manual_pipeline_run"],
        "recovery_options": [bad_option],
        "allowed_agent_tools": ["kernel_resolve_stale_lock"],
        "mirror_event_id": "mev_event_truth",
        "support_bundle_ref": None,
        "status": "active",
        "created_at": "2026-05-07T00:00:00Z",
        "expires_at": expires_at,
        "superseded_by": None,
    }

    with pytest.raises(KernelContractError):
        validate_recovery_event(payload)


def test_recovery_mirror_event_rejects_thin_placeholder_recovery_options() -> None:
    with pytest.raises(KernelContractError):
        assert_recovery_mirror_event(
            {
                "schema_version": "kernel.mirror_event.v1",
                "mirror_event_id": "mev_thin",
                "mirror_source": "kernel",
                "is_kernel_auto_call": True,
                "event_type": MirrorEventType.RECOVERY_STATE.value,
                "severity": "recoverable_error",
                "user_visible_summary": "Recovery is available.",
                "current_state_summary": "Thin options are not valid.",
                "recovery_options": [{"recovery_id": "rcv_thin", "label": "Thin", "agent_tool": "kernel_open_recovery_dialog"}],
                "allowed_agent_tools": ["kernel_open_recovery_dialog"],
            }
        )
