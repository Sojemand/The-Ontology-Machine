from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.capabilities import REQUIRED_PIPELINE_CAPABILITIES
from semantic_control_kernel.repository.ids import generate_id
from semantic_control_kernel.types.adapter_results import AdapterCallResult, MissingCapabilityBlocker, make_missing_capability_blocker


class AdapterResultMixin:
    def missing_capability(
        self,
        *,
        kernel_function: str,
        capability_key: str,
        blocking_reason: str | None = None,
    ) -> MissingCapabilityBlocker:
        capability = REQUIRED_PIPELINE_CAPABILITIES[capability_key]
        return make_missing_capability_blocker(
            kernel_function=kernel_function,
            required_capability=capability.capability_name,
            owner_home=capability.owner_home,
            blocked_until=capability.blocked_until,
            blocking_reason=blocking_reason or capability.blocking_behavior_until_available,
            recovery_state_class=capability.recovery_state_class,
            diagnostics=[
                {
                    "blocked_phase": capability.blocked_until,
                    "capability_status": capability.status,
                    "recommended_implementation_target": capability.recommended_implementation_target,
                    "source_spec_refs": list(capability.source_spec_refs),
                }
            ],
        )

    def ok_result(
        self,
        *,
        kernel_function: str,
        capability_status: str,
        output_refs: Mapping[str, Any] | None = None,
        target_identity_proof: Mapping[str, Any] | None = None,
        receipt_fields: Mapping[str, Any] | None = None,
        diagnostics: list[Mapping[str, Any]] | None = None,
    ) -> AdapterCallResult:
        return self.adapter_result(
            kernel_function=kernel_function,
            capability_status=capability_status,
            status="ok",
            output_refs=output_refs,
            target_identity_proof=target_identity_proof,
            receipt_fields=receipt_fields,
            diagnostics=diagnostics,
        )

    def adapter_result(
        self,
        *,
        kernel_function: str,
        capability_status: str,
        status: str,
        output_refs: Mapping[str, Any] | None = None,
        target_identity_proof: Mapping[str, Any] | None = None,
        receipt_fields: Mapping[str, Any] | None = None,
        diagnostics: list[Mapping[str, Any]] | None = None,
    ) -> AdapterCallResult:
        return AdapterCallResult(
            {
                "adapter_call_id": generate_id("adapter_call_id"),
                "adapter_name": self.adapter_name,
                "capability_status": capability_status,
                "diagnostics": list(diagnostics or ()),
                "kernel_function": kernel_function,
                "output_refs": dict(output_refs or {}),
                "receipt_fields": dict(receipt_fields or {}),
                "status": status,
                "target_identity_proof": dict(target_identity_proof or {}),
            }
        )

    def blocked_by_kernel_precondition(
        self,
        *,
        kernel_function: str,
        capability_status: str,
        summary: str,
        missing_fields: tuple[str, ...] | list[str],
        target_identity_proof: Mapping[str, Any] | None = None,
    ) -> AdapterCallResult:
        return self.adapter_result(
            kernel_function=kernel_function,
            capability_status=capability_status,
            status="blocked_by_kernel_precondition",
            target_identity_proof=target_identity_proof,
            diagnostics=[
                {
                    "code": "blocked_by_kernel_precondition",
                    "summary": summary,
                    "missing_fields": list(missing_fields),
                }
            ],
        )
