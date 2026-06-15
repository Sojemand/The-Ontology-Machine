"""Path-stable adapter stage for embedding provider I/O."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from ..models.types import EmbeddingRuntimeSettings
from .policy import runtime_model_name
from .provider_env import resolved_base_url, resolved_provider_family, resolve_runtime_capability, sanitize_reason
from .provider_http import check_api_available, get_embeddings


def get_embeddings_for_runtime(
    texts: list[str],
    runtime_settings: EmbeddingRuntimeSettings,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider_family: str | None = None,
    api_client: Callable[..., list[list[float]]] = get_embeddings,
) -> list[list[float]]:
    kwargs: dict[str, Any] = {"api_key": api_key}
    if _supports_keyword_argument(api_client, "base_url"):
        kwargs["base_url"] = base_url or resolved_base_url()
    if _supports_keyword_argument(api_client, "provider_family"):
        kwargs["provider_family"] = provider_family or resolved_provider_family(base_url=base_url)
    return api_client(texts, runtime_model_name(runtime_settings), **kwargs)


def _supports_keyword_argument(api_client: Callable[..., list[list[float]]], name: str) -> bool:
    try:
        signature = inspect.signature(api_client)
    except (TypeError, ValueError):  # pragma: no cover - defensive reflection
        return True
    return name in signature.parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
    )


__all__ = [
    "check_api_available",
    "get_embeddings",
    "get_embeddings_for_runtime",
    "resolve_runtime_capability",
    "sanitize_reason",
]
