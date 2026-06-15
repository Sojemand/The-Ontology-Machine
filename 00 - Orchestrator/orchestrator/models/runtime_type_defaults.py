"""Runtime model settings and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .coercion import coerce_int, coerce_str


@dataclass
class LlmRuntimeSettings:
    model: str
    max_output_tokens: int

    def validate(self, *, label: str) -> None:
        if not self.model.strip():
            raise ValueError(f"{label}: model must not be empty.")
        if self.max_output_tokens < 1:
            raise ValueError(f"{label}: max_output_tokens must be greater than 0.")

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "max_output_tokens": self.max_output_tokens}

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        default_model: str,
        default_max_output_tokens: int,
    ) -> "LlmRuntimeSettings":
        payload = data if isinstance(data, dict) else {}
        model = coerce_str(payload.get("model", default_model), default_model).strip() or default_model
        max_output_tokens = coerce_int(
            payload.get("max_output_tokens", default_max_output_tokens),
            default_max_output_tokens,
        )
        if max_output_tokens < 1:
            max_output_tokens = default_max_output_tokens
        return cls(model=model, max_output_tokens=max_output_tokens)


@dataclass
class EmbeddingRuntimeSettings:
    model: str

    def validate(self, *, label: str) -> None:
        if not self.model.strip():
            raise ValueError(f"{label}: model must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model}

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, default_model: str) -> "EmbeddingRuntimeSettings":
        payload = data if isinstance(data, dict) else {}
        model = coerce_str(payload.get("model", default_model), default_model).strip() or default_model
        return cls(model=model)


@dataclass
class OptimizerOcrRuntimeSettings:
    model: str
    max_output_tokens: int
    timeout_seconds: int

    def validate(self, *, label: str) -> None:
        if not self.model.strip():
            raise ValueError(f"{label}: model must not be empty.")
        if self.max_output_tokens < 1:
            raise ValueError(f"{label}: max_output_tokens must be greater than 0.")
        if self.timeout_seconds < 1:
            raise ValueError(f"{label}: timeout_seconds must be greater than 0.")

    def to_dict(self) -> dict[str, Any]:
        self.validate(label="Optimizer OCR")
        return {
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        default_model: str,
        default_max_output_tokens: int,
        default_timeout_seconds: int,
    ) -> "OptimizerOcrRuntimeSettings":
        payload = data if isinstance(data, dict) else {}
        model = coerce_str(payload.get("model", default_model), default_model).strip() or default_model
        max_output_tokens = coerce_int(payload.get("max_output_tokens", default_max_output_tokens), default_max_output_tokens)
        timeout_seconds = coerce_int(payload.get("timeout_seconds", default_timeout_seconds), default_timeout_seconds)
        if max_output_tokens < 1:
            max_output_tokens = default_max_output_tokens
        if timeout_seconds < 1:
            timeout_seconds = default_timeout_seconds
        return cls(model=model, max_output_tokens=max_output_tokens, timeout_seconds=timeout_seconds)


def default_interpreter_runtime_settings() -> LlmRuntimeSettings:
    return LlmRuntimeSettings(model="gpt-5.4", max_output_tokens=8000)


def default_normalizer_runtime_settings() -> LlmRuntimeSettings:
    return LlmRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=15000)


def default_corpus_builder_embeddings_runtime_settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(model="text-embedding-3-small")


def default_optimizer_ocr_runtime_settings() -> OptimizerOcrRuntimeSettings:
    return OptimizerOcrRuntimeSettings(model="gpt-5.4", max_output_tokens=15000, timeout_seconds=120)
