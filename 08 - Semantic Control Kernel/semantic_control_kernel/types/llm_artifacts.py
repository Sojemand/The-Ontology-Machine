from __future__ import annotations

from semantic_control_kernel.types.base import make_contract_types


_CONTRACT_TYPES = (
    ("LLMPromptSnapshot", "kernel.llm_prompt_snapshot.v1"),
    ("LLMResponseCapture", "kernel.llm_response_capture.v1"),
)

globals().update(make_contract_types(_CONTRACT_TYPES, __name__))
