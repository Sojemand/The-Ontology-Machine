from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.repository.paths import stable_hash
from semantic_control_kernel.types.adapter_results import (
    AdapterCallResult,
    MissingCapabilityBlocker,
    make_missing_capability_blocker,
)


def ok_result(kernel_function: str, output_refs: Mapping[str, Any] | None = None) -> AdapterCallResult:
    return AdapterCallResult(
        {
            "adapter_call_id": f"adapter_{stable_hash(kernel_function + str(output_refs))}",
            "adapter_name": "phase9_fake",
            "capability_status": "implemented_in_pipeline",
            "diagnostics": [],
            "kernel_function": kernel_function,
            "output_refs": dict(output_refs or {}),
            "receipt_fields": {},
            "status": "ok",
            "target_identity_proof": {},
        }
    )


def missing(kernel_function: str) -> MissingCapabilityBlocker:
    return make_missing_capability_blocker(
        kernel_function=kernel_function,
        required_capability="Semantic Release Domain Service",
        owner_home="04 - Normalizer",
        blocked_until="phase_19",
        blocking_reason=f"{kernel_function} is not available in the Phase 9 fake.",
        recovery_state_class="support_only_unrecoverable",
        diagnostics=[{"blocked_phase": "phase_19", "capability_status": "deferred_to_phase_19"}],
    )
