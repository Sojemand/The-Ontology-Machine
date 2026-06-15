"""Provider-call workflow for retries and backoff."""
from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import Any

from ..document_io import StructuredDocument
from ..models.config import NormalizerExecutionConfig
from ..providers import ProviderError, RateLimitError
from .types import ModelClient

logger = logging.getLogger(__name__)

NON_RETRIABLE_STATUS_CODES = {400, 401, 403, 404, 422}


def generate_response_text(
    structured_doc: StructuredDocument,
    config: NormalizerExecutionConfig,
    provider: ModelClient,
    messages: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    sleep: Callable[[float], None],
) -> str:
    last_error: Exception | None = None
    total_attempts = config.max_retries + 1
    for attempt in range(1, total_attempts + 1):
        logger.info(
            "Provider-Call fuer %s (%d/%d) | model=%s | structured_outputs=%s | thinking=%s",
            structured_doc.path.name,
            attempt,
            total_attempts,
            config.model,
            config.structured_outputs,
            config.api_thinking_effort,
        )
        try:
            return provider.generate(
                messages=messages,
                schema=schema,
                max_output_tokens=config.max_output_tokens,
                thinking_effort=config.api_thinking_effort,
            )
        except RateLimitError as exc:
            last_error = exc
            if attempt >= total_attempts:
                break
            delay = exc.retry_after if exc.retry_after and exc.retry_after > 0 else config.retry_delay_seconds * (2 ** (attempt - 1))
            logger.warning("Rate limit fuer %s, warte %.1fs (%d/%d)", structured_doc.path.name, delay, attempt, total_attempts)
            _sleep_with_jitter(delay, sleep)
        except ProviderError as exc:
            last_error = exc
            if exc.status_code in NON_RETRIABLE_STATUS_CODES:
                logger.error("Nicht-retriabler Provider-Fehler fuer %s (HTTP %s): %s", structured_doc.path.name, exc.status_code, exc)
                break
            if attempt >= total_attempts:
                break
            delay = config.retry_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Retriabler Provider-Fehler fuer %s, neuer Versuch in %.1fs (%d/%d) | type=%s | status=%s | detail=%s",
                structured_doc.path.name,
                delay,
                attempt,
                total_attempts,
                type(exc).__name__,
                exc.status_code,
                exc,
            )
            _sleep_with_jitter(delay, sleep)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Provider lieferte keine Antwort.")


def _sleep_with_jitter(delay: float, sleep: Callable[[float], None]) -> None:
    if delay <= 0:
        return
    sleep(delay + random.uniform(0, delay * 0.3))
