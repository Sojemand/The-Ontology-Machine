from __future__ import annotations

from typing import Any, Mapping, Sequence

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker, make_missing_capability_blocker

def ok_result(kernel_function: str, output_refs: Mapping[str, Any] | None = None) -> AdapterCallResult:
    return AdapterCallResult(
        {
            "adapter_call_id": f"adapter_{stable_hash(kernel_function + repr(output_refs))}",
            "adapter_name": "phase12_fake",
            "capability_status": "implemented_in_pipeline",
            "diagnostics": [],
            "kernel_function": kernel_function,
            "output_refs": dict(output_refs or {}),
            "receipt_fields": {},
            "status": "ok",
            "target_identity_proof": {},
        }
    )


def owner_error(kernel_function: str, diagnostics: Sequence[Mapping[str, Any]] = ()) -> AdapterCallResult:
    return AdapterCallResult(
        {
            "adapter_call_id": f"adapter_{stable_hash(kernel_function + repr(diagnostics))}",
            "adapter_name": "phase12_fake",
            "capability_status": "implemented_in_pipeline",
            "diagnostics": [dict(item) for item in diagnostics],
            "kernel_function": kernel_function,
            "output_refs": {},
            "receipt_fields": {},
            "status": "owner_error",
            "target_identity_proof": {},
        }
    )


def blocked_precondition(kernel_function: str, *, summary: str, missing_fields: Sequence[str]) -> AdapterCallResult:
    return AdapterCallResult(
        {
            "adapter_call_id": f"adapter_{stable_hash(kernel_function + summary + repr(tuple(missing_fields)))}",
            "adapter_name": "phase12_fake",
            "capability_status": "implemented_in_pipeline",
            "diagnostics": [{"code": "blocked_by_kernel_precondition", "summary": summary, "missing_fields": list(missing_fields)}],
            "kernel_function": kernel_function,
            "output_refs": {},
            "receipt_fields": {},
            "status": "blocked_by_kernel_precondition",
            "target_identity_proof": {},
        }
    )


def missing_merge(kernel_function: str) -> MissingCapabilityBlocker:
    return make_missing_capability_blocker(
        kernel_function=kernel_function,
        required_capability="Multi-Source Merge Domain Service",
        owner_home="05 - Corpus Builder/corpus_builder/semantic_release/",
        blocked_until="phase_19",
        blocking_reason="Multi-Source Merge Domain Service is not available in this fixture.",
        recovery_state_class="support_only_unrecoverable",
        diagnostics=[{"blocked_phase": "phase_19", "capability_status": "deferred_to_phase_19"}],
    )


def missing_release(kernel_function: str) -> MissingCapabilityBlocker:
    return make_missing_capability_blocker(
        kernel_function=kernel_function,
        required_capability="Semantic Release Domain Service",
        owner_home="04 - Normalizer/normalizer_vision/source_authoring/",
        blocked_until="phase_19",
        blocking_reason="Semantic Release Domain Service is not available in this fixture.",
        recovery_state_class="support_only_unrecoverable",
        diagnostics=[{"blocked_phase": "phase_19", "capability_status": "deferred_to_phase_19"}],
    )
