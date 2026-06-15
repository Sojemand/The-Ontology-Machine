"""Path-stable surface for the vision interpreter pipeline."""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.serialization import atomic_json_write
from ..models.types import InterpreterConfig
from ..prompts.types import LoadedPageAsset
from ..prompts.workflow import build_vision_messages
from ..providers import LLMProvider, create_provider
from . import adapter, domain, policy_context, policy_response, validation, workflow
from ..profile_policy import attach_profile, request_has_explicit_profile


def _parse_llm_response(response_text: str) -> dict[str, Any]:
    return policy_response.parse_llm_response(response_text)


def _validate_request(
    request: dict[str, Any] | adapter.LoadedRequest,
    config: InterpreterConfig | None = None,
) -> list[LoadedPageAsset]:
    return validation.validate_request(request, config)


def _estimate_cost(model: str, usage: dict[str, Any]) -> float | None:
    return domain.estimate_cost(model, usage)


def _enrich_output(
    llm_result: dict[str, Any],
    request: dict[str, Any],
    provider_name: str,
    model: str,
) -> dict[str, Any]:
    domain.enrich_output(llm_result, request, provider_name, model)
    policy_context.apply_context_policy(llm_result, request)
    return llm_result


def _call_with_backoff(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    config: InterpreterConfig,
    worker_id: str = "main",
) -> tuple[str | None, str | None]:
    return workflow.call_with_backoff(
        provider,
        messages,
        config,
        worker_id,
        random_module=random,
        time_module=time,
    )


def process_single(
    request_input: Path | dict[str, Any] | adapter.LoadedRequest,
    output_path: Path,
    config: InterpreterConfig,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    return workflow.run_single(
        request_input,
        output_path,
        config,
        provider,
        create_provider_fn=create_provider,
        write_json_fn=atomic_json_write,
        backoff_fn=_call_with_backoff,
    )


def process_batch(
    input_path: Path,
    output_dir: Path,
    config: InterpreterConfig,
    num_workers: int = 1,
    on_progress: Callable[[dict[str, Any], int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    return workflow.run_batch(
        input_path,
        output_dir,
        config,
        num_workers,
        on_progress,
        should_cancel=should_cancel,
        create_provider_fn=create_provider,
        process_single_fn=process_single,
    )


def estimate_tokens(request_input: Path | dict[str, Any], config: InterpreterConfig) -> dict[str, Any]:
    loaded_request = adapter.load_request_payload(request_input)
    if not request_has_explicit_profile(loaded_request.request):
        attach_profile(loaded_request.request, config.interpreter_profile)
    page_assets = validation.validate_request(loaded_request, config)
    messages = build_vision_messages(loaded_request.request, config, page_assets=page_assets)
    return domain.estimate_message_tokens(
        messages,
        config.model,
        config.max_output_tokens,
        label=loaded_request.label,
    )


__all__ = [
    "_call_with_backoff",
    "_enrich_output",
    "_estimate_cost",
    "_parse_llm_response",
    "_validate_request",
    "atomic_json_write",
    "create_provider",
    "estimate_tokens",
    "process_batch",
    "process_single",
    "random",
    "time",
]
