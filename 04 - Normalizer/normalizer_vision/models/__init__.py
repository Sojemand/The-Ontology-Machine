"""Path-stable surface for normalizer config, runtime, and serialization helpers."""
from __future__ import annotations

from .config import (
    NormalizerExecutionConfig,
    NormalizerProjectConfig,
    NormalizerRuntimeSettings,
    load_config,
    save_config,
)
from .results import NormalizationResult
from .serialization import atomic_json_write, load_json, sha256_bytes, sha256_file, utc_now_iso
from .types import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_RUNTIME_THINKING_LABEL,
    FIXED_API_REASONING_EFFORT,
    RUNTIME_SETTINGS_REQUIRED_MESSAGE,
)

__all__ = [
    "NormalizationResult",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_MODEL",
    "DEFAULT_RUNTIME_THINKING_LABEL",
    "FIXED_API_REASONING_EFFORT",
    "NormalizerExecutionConfig",
    "NormalizerProjectConfig",
    "NormalizerRuntimeSettings",
    "RUNTIME_SETTINGS_REQUIRED_MESSAGE",
    "atomic_json_write",
    "load_config",
    "load_json",
    "save_config",
    "sha256_bytes",
    "sha256_file",
    "utc_now_iso",
]
