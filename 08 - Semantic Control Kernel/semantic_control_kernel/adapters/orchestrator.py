from __future__ import annotations

from typing import Any, Callable, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, LONG_RUNNING_TIMEOUT_SECONDS, READ_ONLY_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class OrchestratorAdapter(BasePipelineAdapter):
    adapter_name = "OrchestratorAdapter"
    owner_module = "00 - Orchestrator"
    owner_contract_module = "orchestrator.orchestrator_contract"

    def run_pipeline(
        self,
        request_payload: Mapping[str, Any] | None = None,
        *,
        progress_callback: Callable[[], None] | None = None,
    ) -> AdapterCallResult:
        payload = _owner_payload(request_payload, "run")
        workflow_run_id = str(payload.get("workflow_run_id") or "")
        return self.invoke(
            kernel_function="pipeline_run",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="run",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=(
                "database_path|database_path_hash",
                "artifact_root_path|artifact_root_path_hash",
            ),
            target_identity=dict(payload.get("target_identity") or {}) if isinstance(payload.get("target_identity"), Mapping) else None,
            workflow_run_id=workflow_run_id or None,
            progress_callback=progress_callback,
        )

    def reset_error_cases(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = _owner_payload(request_payload, "reset")
        workflow_run_id = str(payload.get("workflow_run_id") or "")
        return self.invoke(
            kernel_function="manual_pipeline_run",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="reset",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
            mutating=True,
            required_target_proof_fields=("artifact_root_path|artifact_root_path_hash",),
            target_identity=dict(payload.get("target_identity") or {}) if isinstance(payload.get("target_identity"), Mapping) else None,
            workflow_run_id=workflow_run_id or None,
        )

    def inspect_source_sample(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = _owner_payload(request_payload, "inspect_source_document_sample")
        workflow_run_id = str(payload.pop("workflow_run_id", "") or "")
        return self.invoke(
            kernel_function="inspect_source_sample",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="inspect_source_document_sample",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
            workflow_run_id=workflow_run_id or None,
        )

    def kernel_llm_runtime_profile(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = _owner_payload(request_payload, "kernel_llm_runtime_profile")
        return self.invoke(
            kernel_function="semantic_control_kernel_llm_runtime_profile",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="kernel_llm_runtime_profile",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=READ_ONLY_TIMEOUT_SECONDS,
        )

    def kernel_llm_generate(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        payload = _owner_payload(request_payload, "kernel_llm_generate")
        return self.invoke(
            kernel_function="semantic_control_kernel_llm_generate",
            owner_module=self.owner_module,
            owner_contract_module=self.owner_contract_module,
            owner_action="kernel_llm_generate",
            request_payload=payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
        )


def _owner_payload(request_payload: Mapping[str, Any] | None, action: str) -> dict[str, Any]:
    payload = dict(request_payload or {})
    payload.setdefault("action", action)
    return payload
