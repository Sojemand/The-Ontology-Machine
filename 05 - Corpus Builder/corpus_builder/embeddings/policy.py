"""Policy stage for embedding config and runtime interpretation."""

from __future__ import annotations

from ..models.types import EmbeddingConfig, EmbeddingRuntimeSettings


def normalize_positive_int(value: object, *, fallback: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(1, normalized)


def config_batch_size(config: EmbeddingConfig) -> int:
    return normalize_positive_int(getattr(config, "batch_size", 50), fallback=50)


def config_max_text_chars(config: EmbeddingConfig) -> int:
    return normalize_positive_int(getattr(config, "max_text_chars", 12000), fallback=12000)


def config_expected_dimensions(config: EmbeddingConfig) -> int:
    defaults = EmbeddingConfig()
    return normalize_positive_int(
        getattr(config, "dimensions", defaults.dimensions),
        fallback=defaults.dimensions,
    )


def runtime_model_name(runtime_settings: EmbeddingRuntimeSettings) -> str:
    model = str(getattr(runtime_settings, "model", "") or "").strip()
    if not model:
        raise ValueError("runtime_settings.model fehlt oder ist ungueltig.")
    return model
