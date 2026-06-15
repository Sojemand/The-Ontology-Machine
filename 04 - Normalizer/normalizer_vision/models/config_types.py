"""Dataclass carriers for normalizer configuration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .types import (
    DEFAULT_MAX_BATCH_FILES,
    DEFAULT_MAX_BATCH_WORKERS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MAX_STRUCTURED_BYTES,
    DEFAULT_MODEL,
    DEFAULT_RUNTIME_THINKING_LABEL,
    DEFAULT_TIMEOUT_SECONDS,
    FIXED_API_REASONING_EFFORT,
    PROJECTION_HINT_MODE_OPTIONS,
)


@dataclass
class NormalizerProjectConfig:
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = 3
    retry_delay_seconds: int = 5
    structured_outputs: bool = True
    default_workers: int = 4
    max_structured_bytes: int = DEFAULT_MAX_STRUCTURED_BYTES
    max_batch_files: int = DEFAULT_MAX_BATCH_FILES
    max_batch_workers: int = DEFAULT_MAX_BATCH_WORKERS
    taxonomy_profile_id: str = ""
    projection_hint_mode: str = "advisory"

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds muss positiv sein")
        if self.max_retries < 0:
            raise ValueError("max_retries muss >= 0 sein")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds muss >= 0 sein")
        if self.default_workers < 1:
            raise ValueError("default_workers muss >= 1 sein")
        if self.max_structured_bytes <= 0:
            raise ValueError("max_structured_bytes muss positiv sein")
        if self.max_batch_files < 1:
            raise ValueError("max_batch_files muss >= 1 sein")
        if self.max_batch_workers < 1:
            raise ValueError("max_batch_workers muss >= 1 sein")
        if self.default_workers > self.max_batch_workers:
            raise ValueError("default_workers darf max_batch_workers nicht ueberschreiten")
        if self.projection_hint_mode not in PROJECTION_HINT_MODE_OPTIONS:
            raise ValueError(f"ungueltiges projection_hint_mode: {self.projection_hint_mode}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def build_execution_config(self, runtime_settings: "NormalizerRuntimeSettings") -> "NormalizerExecutionConfig":
        return NormalizerExecutionConfig(
            model=runtime_settings.model,
            timeout_seconds=self.timeout_seconds,
            max_output_tokens=runtime_settings.max_output_tokens,
            max_retries=self.max_retries,
            retry_delay_seconds=self.retry_delay_seconds,
            structured_outputs=self.structured_outputs,
            default_workers=self.default_workers,
            max_structured_bytes=self.max_structured_bytes,
            max_batch_files=self.max_batch_files,
            max_batch_workers=self.max_batch_workers,
            taxonomy_profile_id=self.taxonomy_profile_id,
            projection_hint_mode=self.projection_hint_mode,
        )


@dataclass(frozen=True)
class NormalizerRuntimeSettings:
    model: str = DEFAULT_MODEL
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("runtime_settings.model darf nicht leer sein.")
        if self.max_output_tokens <= 0:
            raise ValueError("runtime_settings.max_output_tokens muss positiv sein.")

    @property
    def thinking_effort(self) -> str:
        return DEFAULT_RUNTIME_THINKING_LABEL

    @property
    def api_thinking_effort(self) -> str:
        return FIXED_API_REASONING_EFFORT

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "max_output_tokens": self.max_output_tokens}


@dataclass(frozen=True)
class NormalizerExecutionConfig:
    model: str
    timeout_seconds: int
    max_output_tokens: int
    max_retries: int
    retry_delay_seconds: int
    structured_outputs: bool
    default_workers: int
    max_structured_bytes: int
    max_batch_files: int
    max_batch_workers: int
    taxonomy_profile_id: str
    projection_hint_mode: str

    def __post_init__(self) -> None:
        NormalizerProjectConfig(
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            retry_delay_seconds=self.retry_delay_seconds,
            structured_outputs=self.structured_outputs,
            default_workers=self.default_workers,
            max_structured_bytes=self.max_structured_bytes,
            max_batch_files=self.max_batch_files,
            max_batch_workers=self.max_batch_workers,
            taxonomy_profile_id=self.taxonomy_profile_id,
            projection_hint_mode=self.projection_hint_mode,
        )
        NormalizerRuntimeSettings(model=self.model, max_output_tokens=self.max_output_tokens)

    @property
    def thinking_effort(self) -> str:
        return DEFAULT_RUNTIME_THINKING_LABEL

    @property
    def api_thinking_effort(self) -> str:
        return FIXED_API_REASONING_EFFORT
