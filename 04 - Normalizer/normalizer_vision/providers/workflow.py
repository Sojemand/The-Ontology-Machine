"""Workflow stage for Normalizer OpenAI generation."""
from __future__ import annotations

import logging
from typing import Any

from .base import ProviderError, RateLimitError, sanitize_secret_text
from .payload import build_payload, payload_bytes
from .policy import schema_mode
from .response import ParsedResponse, parse_response
from .transport import build_headers, parse_retry_after, post_responses, request_id, responses_url, requests

logger = logging.getLogger(__name__)
_SCHEMA_FALLBACK_STATUS_CODES = {400, 422}
_SCHEMA_REJECTION_MARKERS = (
    "json_schema",
    "response_format",
    "text.format",
    "schema",
    "strict",
)


def generate_text_response(
    provider: Any,
    *,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> str:
    headers = build_headers(provider.api_key)
    endpoint = responses_url(provider.base_url)
    started_at = provider._log_request(messages, max_output_tokens, provider.model)
    response = _post_with_fallbacks(
        provider,
        endpoint=endpoint,
        headers=headers,
        messages=messages,
        schema=schema,
        max_output_tokens=max_output_tokens,
        thinking_effort=thinking_effort,
    )
    parsed = _handle_response(provider, response, started_at, max_output_tokens)
    if parsed.output_text and parsed.json_is_valid:
        return parsed.output_text
    if parsed.incomplete_reason:
        raise ProviderError(
            f"Provider Responses API lieferte unvollstaendigen Output: {parsed.incomplete_reason}. "
            "runtime_settings.max_output_tokens muss explizit angepasst werden."
        )
    if parsed.output_text:
        logger.warning(
            "[%s] Ungueltiges JSON im Modell-Output | response_id=%s | out_tokens=%d/%d | text_suffix=%s",
            provider.provider_name,
            provider._last_response_id or "-",
            parsed.output_tokens,
            max_output_tokens,
            sanitize_secret_text(parsed.output_text[-300:]),
        )
        raise ProviderError("Provider lieferte ungueltiges JSON im Modell-Output")
    raise ProviderError("Provider Responses API lieferte keinen Text-Output")


def _post_with_fallbacks(
    provider: Any,
    *,
    endpoint: str,
    headers: dict[str, str],
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_output_tokens: int,
    thinking_effort: str,
) -> Any:
    payload = build_payload(provider.model, messages, schema, max_output_tokens, thinking_effort)
    primary_mode = schema_mode(schema)
    try:
        response = _post_once(provider, endpoint, payload, headers, primary_mode)
        if _should_retry_as_json_object(response, primary_mode):
            logger.warning(
                "[%s] Structured-Output-Schema wurde vom Provider abgelehnt, wechsle fuer diesen Versuch auf json_object fallback | status=%s | request_id=%s",
                provider.provider_name,
                response.status_code,
                request_id(response),
            )
            return _post_json_object_fallback(provider, endpoint, headers, messages, max_output_tokens, thinking_effort)
        return response
    except requests.ConnectionError as exc:
        logger.warning(
            "[%s] Verbindungsfehler bei %s | model=%s | schema=%s | detail=%s",
            provider.provider_name,
            endpoint,
            provider.model,
            primary_mode,
            provider._exception_details(exc),
        )
        if primary_mode == "json_schema":
            logger.warning("[%s] Structured-Output-Transport fehlgeschlagen, wechsle fuer diesen Versuch auf json_object fallback", provider.provider_name)
            return _post_json_object_fallback(provider, endpoint, headers, messages, max_output_tokens, thinking_effort)
        raise ProviderError(f"Provider nicht erreichbar: {exc}") from exc
    except requests.Timeout:
        raise ProviderError(f"Provider Timeout nach {provider.timeout}s")
    except requests.RequestException as exc:
        raise ProviderError(f"Provider Anfrage fehlgeschlagen: {exc}") from exc


def _post_once(provider: Any, endpoint: str, payload: dict[str, Any], headers: dict[str, str], schema_label: str) -> Any:
    size = payload_bytes(payload)
    logger.info(
        "[%s] POST %s | schema=%s | payload_bytes=%s | timeout=(10,%ds)",
        provider.provider_name,
        endpoint,
        schema_label,
        size if size is not None else "?",
        provider.timeout,
    )
    response = post_responses(provider._transport, endpoint=endpoint, payload=payload, headers=headers, timeout=provider.timeout)
    logger.info(
        "[%s] HTTP %d von %s | request_id=%s | schema=%s",
        provider.provider_name,
        response.status_code,
        endpoint,
        request_id(response),
        schema_label,
    )
    return response


def _post_json_object_fallback(
    provider: Any,
    endpoint: str,
    headers: dict[str, str],
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    thinking_effort: str,
) -> Any:
    fallback_payload = build_payload(provider.model, messages, None, max_output_tokens, thinking_effort)
    try:
        return _post_once(provider, endpoint, fallback_payload, headers, "json_object")
    except requests.ConnectionError as fallback_exc:
        logger.warning(
            "[%s] Verbindungsfehler auch im json_object fallback | detail=%s",
            provider.provider_name,
            provider._exception_details(fallback_exc),
        )
        raise ProviderError(f"Provider nicht erreichbar: {fallback_exc}") from fallback_exc
    except requests.Timeout:
        raise ProviderError(f"Provider Timeout nach {provider.timeout}s")
    except requests.RequestException as fallback_exc:
        raise ProviderError(f"Provider Anfrage fehlgeschlagen: {fallback_exc}") from fallback_exc


def _should_retry_as_json_object(response: Any, primary_mode: str) -> bool:
    if primary_mode != "json_schema" or response.status_code not in _SCHEMA_FALLBACK_STATUS_CODES:
        return False
    body = str(getattr(response, "text", "") or "").lower()
    return any(marker in body for marker in _SCHEMA_REJECTION_MARKERS)


def _handle_response(provider: Any, response: Any, started_at: float, max_output_tokens: int) -> ParsedResponse:
    if response.status_code == 429:
        logger.warning(
            "[%s] Rate limit | request_id=%s | retry_after=%s",
            provider.provider_name,
            request_id(response),
            response.headers.get("retry-after"),
        )
        raise RateLimitError(retry_after=parse_retry_after(response.headers.get("retry-after")))
    if response.status_code != 200:
        logger.warning(
            "[%s] Provider API Fehler %d | request_id=%s | body=%s",
            provider.provider_name,
            response.status_code,
            request_id(response),
            sanitize_secret_text(response.text[:500]),
        )
        raise ProviderError(
            f"Provider API Fehler {response.status_code}: {sanitize_secret_text(response.text[:500])}",
            status_code=response.status_code,
        )
    parsed = parse_response(response, fallback_model=provider.model)
    provider._last_usage = parsed.usage
    provider._last_model = parsed.model
    provider._last_response_id = parsed.response_id
    provider._log_response(started_at, provider._last_model or provider.model)
    return parsed
