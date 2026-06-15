from __future__ import annotations

from typing import Any, Mapping

from semantic_control_kernel.adapters.base import BasePipelineAdapter, LONG_RUNNING_TIMEOUT_SECONDS
from semantic_control_kernel.types.adapter_results import AdapterCallResult


class InterpreterAdapter(BasePipelineAdapter):
    adapter_name = "InterpreterAdapter"

    def interpret_document(self, request_payload: Mapping[str, Any] | None = None) -> AdapterCallResult:
        return self.invoke(
            kernel_function="interpret_document",
            owner_module="02 - Interpreter",
            owner_contract_module="llm_interpreter.orchestrator_contract",
            owner_action="interpret_document",
            request_payload=request_payload,
            capability_status="implemented_in_pipeline",
            timeout_seconds=LONG_RUNNING_TIMEOUT_SECONDS,
        )
