from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, LONG_RUNNING_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class OptimizerAdapter(BasePipelineAdapter):
    adapter_name = "OptimizerAdapter"

    def classify_document(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self._invoke_optimizer("classify_document", request_payload)

    def extract_document(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self._invoke_optimizer("extract_document", request_payload)

    def _invoke_optimizer(self, owner_action: str, request_payload: Mapping[str, Any] | None) -> AdapterCallResult:
        return self.invoke(
            kernel_function=owner_action,
            owner_module="01 - Optimizer",
            owner_contract_module="ingestion_layer_vision.orchestrator_contract",
            owner_action=owner_action,
            request_payload=request_payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
        )
