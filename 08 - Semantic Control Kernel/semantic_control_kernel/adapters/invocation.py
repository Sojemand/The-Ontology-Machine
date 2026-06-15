from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.invocation_files import adapter_call_files, relative_ref, write_json
from semantic_control_kernel.adapters.invocation_process import execute_owner_process
from semantic_control_kernel.adapters.invocation_types import AdapterInvocation, OwnerBoundary
from semantic_control_kernel.adapters.owner_response import (
    _derived_target_identity_proof,
    _load_owner_response,
    _mapping_field,
    _missing_target_proof_fields,
    _owner_error_summary,
    _owner_status,
    _owner_summary,
    _target_identity_mismatches,
)
from semantic_control_kernel.adapters.phase19_requests import PHASE19_OWNER_REQUEST_SCHEMA_VERSION, phase19_request_fingerprint
from semantic_control_kernel.repository.atomic_json import AtomicJsonStore
from semantic_control_kernel.repository.hard_cap import KernelStateHardCapService
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.repository.paths import StatePaths, utc_iso
from semantic_control_kernel.types.adapter_results import AdapterCallResult, make_call_request, make_call_response, make_call_result


def invoke_owner_contract(invocation: AdapterInvocation) -> AdapterCallResult:
    call_id = generate_id("adapter_call_id")
    paths = StatePaths.from_state_root(invocation.state_root)
    json_store = AtomicJsonStore(paths, "adapter_calls")
    files = adapter_call_files(paths, call_id)
    files.call_dir.mkdir(parents=True, exist_ok=True)

    request = make_call_request(
        adapter_call_id=call_id,
        kernel_function=invocation.kernel_function,
        adapter_name=invocation.boundary.adapter_name,
        owner_module=invocation.boundary.owner_module,
        owner_contract_module=invocation.boundary.owner_contract_module,
        owner_action=invocation.boundary.owner_action,
        request_payload=_owner_request_payload(invocation, call_id),
        target_identity=invocation.target_identity,
        state_snapshot_identity=invocation.state_snapshot_identity,
        timeout_seconds=invocation.boundary.timeout_seconds,
        created_at=utc_iso(),
    )
    write_json(json_store, files.request_path, request.to_dict())

    execution = execute_owner_process(invocation, call_id=call_id, paths=paths, files=files)
    parsed = _parse_owner_response(files.raw_response_path, execution["status"], execution["diagnostics"])
    status, owner_status, owner_summary, target_proof, output_refs, receipt_fields = _owner_fields(parsed, execution)
    status = _apply_target_proof_rules(status, invocation, target_proof, execution["diagnostics"])

    completed_at = utc_iso()
    response = make_call_response(
        adapter_call_id=call_id,
        status=status,
        owner_status=owner_status,
        owner_response_ref=relative_ref(invocation.state_root, files.raw_response_path),
        owner_response_summary=owner_summary,
        target_identity_proof=target_proof,
        diagnostics=execution["diagnostics"],
        completed_at=completed_at,
    )
    result = make_call_result(
        adapter_call_id=call_id,
        kernel_function=invocation.kernel_function,
        adapter_name=invocation.boundary.adapter_name,
        capability_status=invocation.boundary.capability_status,
        status=status,
        target_identity_proof=target_proof,
        output_refs=output_refs,
        diagnostics=execution["diagnostics"],
        receipt_fields=receipt_fields,
    )
    write_json(json_store, files.response_path, response.to_dict())
    write_json(json_store, files.result_path, result.to_dict())
    write_json(json_store, files.diagnostics_path, {"adapter_call_id": call_id, "diagnostics": execution["diagnostics"]})
    KernelStateHardCapService(paths).prune_raw_adapter_calls()
    return result


def _owner_request_payload(invocation: AdapterInvocation, call_id: str) -> dict[str, Any]:
    payload = dict(invocation.request_payload)
    if payload.get("schema_version") == PHASE19_OWNER_REQUEST_SCHEMA_VERSION:
        payload.setdefault("adapter_call_id", call_id)
        if invocation.workflow_run_id:
            payload.setdefault("workflow_run_id", invocation.workflow_run_id)
        payload.setdefault("requested_at", utc_iso())
        payload["request_fingerprint"] = phase19_request_fingerprint(payload)
    return payload


def _parse_owner_response(raw_response_path, status: str, diagnostics: list[dict[str, Any]]) -> Mapping[str, Any] | None:
    if status in {"timeout", "owner_error"} and raw_response_path.read_text(encoding="utf-8") == "":
        return None
    parsed = _load_owner_response(raw_response_path, diagnostics)
    if parsed is None and status != "timeout":
        diagnostics.append({"code": "owner_response_missing_or_invalid"})
    return parsed


def _owner_fields(parsed: Mapping[str, Any] | None, execution: dict[str, Any]):
    if parsed is None:
        status = execution["status"]
        if status not in {"timeout", "owner_error"}:
            status = "invalid_owner_response"
        return status, execution["owner_status"], {}, {}, {}, {}
    owner_status = _owner_status(parsed)
    owner_summary = _owner_summary(parsed)
    target_proof = _derived_target_identity_proof(_mapping_field(parsed, "target_identity_proof"), _output_refs(parsed))
    receipt_fields = _mapping_field(parsed, "receipt_fields")
    _extend_owner_diagnostics(parsed, execution["diagnostics"], owner_status)
    if owner_status == "ok":
        status = "ok"
    elif owner_status == "missing_capability":
        status = "missing_capability"
    else:
        status = "owner_error"
    return status, owner_status, owner_summary, target_proof, _output_refs(parsed), receipt_fields


def _output_refs(parsed: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping_field(parsed, "output_refs") or _mapping_field(parsed, "detail")


def _extend_owner_diagnostics(parsed: Mapping[str, Any], diagnostics: list[dict[str, Any]], owner_status: str) -> None:
    owner_diagnostics = parsed.get("diagnostics", [])
    if isinstance(owner_diagnostics, list):
        diagnostics.extend(item for item in owner_diagnostics if isinstance(item, dict))
    owner_error = _owner_error_summary(parsed)
    if owner_error and owner_status not in {"ok", "missing_capability"}:
        diagnostics.append({"code": "owner_response_error", "summary": owner_error})


def _apply_target_proof_rules(status: str, invocation: AdapterInvocation, target_proof: dict[str, Any], diagnostics: list[dict[str, Any]]) -> str:
    if status == "ok" and invocation.target_identity:
        mismatched_fields = _target_identity_mismatches(invocation.target_identity, target_proof)
        if mismatched_fields:
            diagnostics.append({"code": "target_identity_changed", "mismatched_fields": mismatched_fields})
            return "target_identity_changed"
    if status == "ok" and invocation.boundary.mutating:
        missing_fields = _missing_target_proof_fields(target_proof, invocation.boundary.required_target_proof_fields)
        if missing_fields:
            diagnostics.append({"code": "target_identity_unproven", "missing_fields": missing_fields})
            return "target_identity_unproven"
    return status


__all__ = [
    "AdapterInvocation",
    "OwnerBoundary",
    "_derived_target_identity_proof",
    "invoke_owner_contract",
]
