from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from semantic_control_kernel.types.adapter_results import (
    AdapterCallRequest,
    AdapterCallResponse,
    AdapterCallResult,
    MissingCapabilityBlocker,
    _copy_mapping,
)


def make_call_request(
    *,
    adapter_call_id: str,
    kernel_function: str,
    adapter_name: str,
    owner_module: str,
    owner_contract_module: str,
    owner_action: str,
    request_payload: Mapping[str, Any],
    target_identity: Mapping[str, Any] | None,
    state_snapshot_identity: Mapping[str, Any] | None,
    timeout_seconds: float | None,
    created_at: str,
) -> AdapterCallRequest:
    return AdapterCallRequest(
        {
            "adapter_call_id": adapter_call_id,
            "adapter_name": adapter_name,
            "created_at": created_at,
            "kernel_function": kernel_function,
            "owner_action": owner_action,
            "owner_contract_module": owner_contract_module,
            "owner_module": owner_module,
            "request_payload": _copy_mapping(request_payload),
            "state_snapshot_identity": _copy_mapping(state_snapshot_identity),
            "target_identity": _copy_mapping(target_identity),
            "timeout_seconds": timeout_seconds,
        }
    )


def make_call_response(
    *,
    adapter_call_id: str,
    status: str,
    owner_status: str,
    owner_response_ref: str | None,
    owner_response_summary: Mapping[str, Any],
    target_identity_proof: Mapping[str, Any] | None,
    diagnostics: list[Mapping[str, Any]],
    completed_at: str,
) -> AdapterCallResponse:
    return AdapterCallResponse(
        {
            "adapter_call_id": adapter_call_id,
            "completed_at": completed_at,
            "diagnostics": deepcopy(diagnostics),
            "owner_response_ref": owner_response_ref,
            "owner_response_summary": _copy_mapping(owner_response_summary),
            "owner_status": owner_status,
            "status": status,
            "target_identity_proof": _copy_mapping(target_identity_proof),
        }
    )


def make_call_result(
    *,
    adapter_call_id: str,
    kernel_function: str,
    adapter_name: str,
    capability_status: str,
    status: str,
    target_identity_proof: Mapping[str, Any] | None,
    output_refs: Mapping[str, Any] | None,
    diagnostics: list[Mapping[str, Any]],
    receipt_fields: Mapping[str, Any] | None,
) -> AdapterCallResult:
    return AdapterCallResult(
        {
            "adapter_call_id": adapter_call_id,
            "adapter_name": adapter_name,
            "capability_status": capability_status,
            "diagnostics": deepcopy(diagnostics),
            "kernel_function": kernel_function,
            "output_refs": _copy_mapping(output_refs),
            "receipt_fields": _copy_mapping(receipt_fields),
            "status": status,
            "target_identity_proof": _copy_mapping(target_identity_proof),
        }
    )


def make_missing_capability_blocker(
    *,
    kernel_function: str,
    required_capability: str,
    owner_home: str,
    blocked_until: str,
    blocking_reason: str,
    recovery_state_class: str,
    diagnostics: list[Mapping[str, Any]],
) -> MissingCapabilityBlocker:
    return MissingCapabilityBlocker(
        {
            "blocked_until": blocked_until,
            "blocking_reason": blocking_reason,
            "diagnostics": deepcopy(diagnostics),
            "kernel_function": kernel_function,
            "owner_home": owner_home,
            "recovery_state_class": recovery_state_class,
            "required_capability": required_capability,
        }
    )
