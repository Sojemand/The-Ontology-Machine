"""Workflow stage for retries, single-run execution, and batch orchestration."""
from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.types import InterpreterConfig
from ..prompts import build_message_snapshot, build_vision_messages
from ..prompts.projection_hint import prune_empty_projection_hint
from ..providers import LLMProvider, ProviderError, RateLimitError
from . import adapter, batch, debug, domain, policy_context, policy_response, results, validation
from ..profile_policy import attach_profile, request_has_explicit_profile
from .projection_hint_policy import normalize_projection_hint
from .validation_repair import repair_validation_failure
from .types import DebugBundleState, ProviderCall, RequestInput
logger = logging.getLogger(__name__)
_NON_RETRIABLE_STATUS_CODES = {400, 401, 403, 404, 413, 422}
def call_with_backoff(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    config: InterpreterConfig,
    worker_id: str = "main",
    *,
    random_module: Any,
    time_module: Any,
) -> tuple[str | None, str | None]:
    total_attempts = config.max_retries + 1
    last_error: ProviderError | None = None
    for attempt in range(1, total_attempts + 1):
        try:
            return provider.generate(
                messages=messages,
                schema=None,
                max_output_tokens=config.max_output_tokens,
                thinking_effort=config.api_thinking_effort,
            ), None
        except RateLimitError as exc:
            last_error = exc
            if attempt >= total_attempts:
                break
            wait = exc.retry_after if exc.retry_after and exc.retry_after > 0 else config.retry_delay_seconds * (2 ** (attempt - 1))
            wait = max(0.0, wait)
            if wait > 0:
                wait += random_module.uniform(0, wait * 0.3)
                logger.warning("[%s] Rate limit, warte %.1fs (%d/%d)", worker_id, wait, attempt, total_attempts)
                time_module.sleep(wait)
        except ProviderError as exc:
            last_error = exc
            if exc.status_code and exc.status_code in _NON_RETRIABLE_STATUS_CODES:
                logger.error("[%s] Nicht-retriable Provider-Fehler (HTTP %d): %s", worker_id, exc.status_code, exc)
                break
            logger.error("[%s] Provider-Fehler: %s (%d/%d)", worker_id, exc, attempt, total_attempts)
            if attempt < total_attempts:
                time_module.sleep(config.retry_delay_seconds)
    return None, str(last_error) if last_error else "LLM-Antwort leer nach allen Retries"
def run_single(
    request_input: RequestInput,
    output_path: Path,
    config: InterpreterConfig,
    provider: LLMProvider | None,
    *,
    create_provider_fn: Callable[..., LLMProvider],
    write_json_fn: Callable[[Path, dict[str, Any]], None],
    backoff_fn: Callable[[LLMProvider, list[dict[str, Any]], InterpreterConfig, str], tuple[str | None, str | None]],
) -> dict[str, Any]:
    label = str(getattr(request_input, "name", "request.json"))
    state = DebugBundleState(label=label)
    try:
        loaded_request = adapter.load_request_payload(request_input)
        request = loaded_request.request
        if not request_has_explicit_profile(request):
            attach_profile(request, config.interpreter_profile)
        label = loaded_request.label
        page_assets = validation.validate_request(loaded_request, config)
        state.label = label
        state.request = request
        state.request_path = None if loaded_request.request_path is None else str(loaded_request.request_path)
    except Exception as exc:
        return _error_result(config, state, output_path, "load_request", exc)
    if provider is None:
        try:
            provider = create_provider_fn(config.model, timeout=config.timeout_seconds, base_url=config.api_base_url)
        except Exception as exc:
            return _error_result(config, state, output_path, "create_provider", exc)
    try:
        messages = build_vision_messages(request, config, page_assets=page_assets)
        state.message_snapshot = build_message_snapshot(messages)
    except Exception as exc:
        return _error_result(config, state, output_path, "build_messages", exc)
    try:
        call = _run_provider_call(provider, messages, config, label, backoff_fn)
        state.raw_provider_text = call.response_text
    except Exception as exc:
        return _error_result(config, state, output_path, "call_provider", exc)
    try:
        llm_result = policy_response.parse_llm_response(call.response_text)
        state.parsed_payload = copy.deepcopy(llm_result)
    except Exception as exc:
        return _error_result(config, state, output_path, "parse_response", exc)
    try:
        normalize_projection_hint(llm_result, request)
    except Exception as exc:
        return _error_result(config, state, output_path, "validate_model_output", exc)
    try:
        validation.validate_llm_output_shape(llm_result, request)
    except Exception as exc:
        try:
            llm_result, repair_call = repair_validation_failure(
                provider,
                config,
                label,
                llm_result,
                exc,
                lambda current_provider, repair_messages, current_config, repair_label: _run_provider_call(
                    current_provider,
                    repair_messages,
                    current_config,
                    repair_label,
                    backoff_fn,
                ),
            )
            state.raw_provider_text = repair_call.response_text
            state.parsed_payload = copy.deepcopy(llm_result)
            normalize_projection_hint(llm_result, request)
            validation.validate_llm_output_shape(llm_result, request)
            call = repair_call
        except Exception as repair_exc:
            return _error_result(config, state, output_path, "validate_model_output", repair_exc)
    try:
        domain.enrich_output(llm_result, request, call.provider_name, call.resolved_model)
        policy_context.apply_context_policy(llm_result, request)
        prune_empty_projection_hint(llm_result.get("context", {}))
        state.persisted_payload = copy.deepcopy(llm_result)
    except Exception as exc:
        return _error_result(config, state, output_path, "enrich_output", exc)
    try:
        validation.validate_persisted_output_shape(llm_result)
    except Exception as exc:
        return _error_result(config, state, output_path, "validate_persisted_output", exc)
    try:
        adapter.write_output(output_path, llm_result, write_json_fn)
    except Exception as exc:
        return _error_result(config, state, output_path, "write_output", exc)
    debug_bundle_path = debug.write_debug_bundle(config, state, failed_stage=None, error=None)
    return results.build_success_result(label, output_path, llm_result, call, debug_bundle_path=debug_bundle_path)
def run_batch(
    input_path: Path,
    output_dir: Path,
    config: InterpreterConfig,
    num_workers: int,
    on_progress: Callable[[dict[str, Any], int, int], None] | None,
    *,
    should_cancel: Callable[[], bool] | None = None,
    create_provider_fn: Callable[..., LLMProvider],
    process_single_fn: Callable[[RequestInput, Path, InterpreterConfig, LLMProvider | None], dict[str, Any]],
) -> dict[str, Any]:
    batch.validate_num_workers(num_workers, config.max_workers)
    files = adapter.collect_batch_files(input_path)
    if not files:
        return {"ok": 0, "error": 0, "total": 0, "total_cost_usd": None, "results": []}
    output_dir.mkdir(parents=True, exist_ok=True)
    planned = adapter.plan_batch_outputs(files, output_dir)
    results: list[dict[str, Any]] = [None] * len(files)
    if num_workers <= 1:
        batch.run_sequential_batch(planned, results, len(files), config, on_progress, create_provider_fn, process_single_fn, should_cancel)
    else:
        batch.run_parallel_batch(planned, results, len(files), config, on_progress, create_provider_fn, process_single_fn, num_workers, should_cancel)
    ok = sum(1 for result in results if result["status"] in ("ok", "ok_review"))
    error = sum(1 for result in results if result["status"] in ("error", "cancelled"))
    total_cost = sum(result.get("cost_estimate_usd") or 0 for result in results)
    return {"ok": ok, "error": error, "total": len(files), "total_cost_usd": round(total_cost, 6) if total_cost else None, "results": results}
def _run_provider_call(
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    config: InterpreterConfig,
    label: str,
    backoff_fn: Callable[[LLMProvider, list[dict[str, Any]], InterpreterConfig, str], tuple[str | None, str | None]],
) -> ProviderCall:
    response_text, backoff_error = backoff_fn(provider, messages, config, label)
    if not response_text:
        raise ProviderError(backoff_error or "LLM-Antwort leer nach allen Retries")
    return ProviderCall(
        response_text=response_text,
        provider_name=provider.provider_name,
        resolved_model=getattr(provider, "_last_model", "") or config.model,
        usage=getattr(provider, "_last_usage", {}),
    )
def _error_result(
    config: InterpreterConfig,
    state: DebugBundleState,
    output_path: Path,
    stage: str,
    exc: Exception,
) -> dict[str, Any]:
    debug_bundle_path = debug.write_debug_bundle(config, state, failed_stage=stage, error=exc)
    return results.build_error_result(state.label, output_path, stage, exc, debug_bundle_path=debug_bundle_path)
