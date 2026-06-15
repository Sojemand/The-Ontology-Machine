from __future__ import annotations

from semantic_control_kernel.workflows.llm_calls.function_registry import (
    LLM_FUNCTION_NAMES,
    get_llm_function_definition,
    get_llm_function_registry,
)

__all__ = [
    "LLMCallRunner",
    "LLM_FUNCTION_NAMES",
    "get_llm_function_definition",
    "get_llm_function_registry",
]


def __getattr__(name: str):
    if name == "LLMCallRunner":
        from semantic_control_kernel.workflows.llm_calls.runner import LLMCallRunner

        return LLMCallRunner
    raise AttributeError(name)
