from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, LONG_RUNNING_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class NormalizerAdapter(BasePipelineAdapter):
    adapter_name = "NormalizerAdapter"

    def normalize_document(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self.invoke(
            kernel_function="normalize_document",
            owner_module="04 - Normalizer",
            owner_contract_module="normalizer_vision.orchestrator_contract",
            owner_action="normalize_document",
            request_payload=request_payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
        )
