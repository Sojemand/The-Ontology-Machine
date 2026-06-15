"""Aggregate runtime settings state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .coercion import coerce_int
from .runtime_provider_settings import (
    _DEFAULT_OPENAI_BASE_URL,
    ProviderEndpointSettings,
    default_embeddings_provider_settings,
    default_llm_shared_provider_settings,
    default_optimizer_ocr_provider_settings,
)
from .runtime_type_defaults import (
    EmbeddingRuntimeSettings,
    LlmRuntimeSettings,
    OptimizerOcrRuntimeSettings,
    default_corpus_builder_embeddings_runtime_settings,
    default_interpreter_runtime_settings,
    default_normalizer_runtime_settings,
    default_optimizer_ocr_runtime_settings,
)


_OPTIMIZER_OCR_PROVIDER_FAMILIES = {"openai_responses", "openai_chat"}


@dataclass
class RuntimeSettingsState:
    schema_version: int = 1
    llm_shared_provider: ProviderEndpointSettings = field(default_factory=default_llm_shared_provider_settings)
    embeddings_provider: ProviderEndpointSettings = field(default_factory=default_embeddings_provider_settings)
    optimizer_ocr_provider: ProviderEndpointSettings = field(default_factory=default_optimizer_ocr_provider_settings)
    interpreter: LlmRuntimeSettings = field(default_factory=default_interpreter_runtime_settings)
    normalizer: LlmRuntimeSettings = field(default_factory=default_normalizer_runtime_settings)
    corpus_builder_embeddings: EmbeddingRuntimeSettings = field(default_factory=default_corpus_builder_embeddings_runtime_settings)
    optimizer_ocr: OptimizerOcrRuntimeSettings = field(default_factory=default_optimizer_ocr_runtime_settings)

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"runtime_settings.json has invalid schema_version: {self.schema_version}")
        self.llm_shared_provider.validate(label="LLM Shared Provider")
        self.embeddings_provider.validate(label="Embeddings Provider")
        self.optimizer_ocr_provider.validate(label="Optimizer OCR Provider")
        if not self.llm_shared_provider.supports_llm():
            raise ValueError("LLM Shared Provider does not support LLM runtime paths.")
        if not self.embeddings_provider.supports_embeddings():
            raise ValueError("Embeddings Provider does not support embedding runtime paths.")
        if not self.optimizer_ocr_provider.supports_llm():
            raise ValueError("Optimizer OCR Provider does not support LLM runtime paths.")
        if self.optimizer_ocr_provider.normalized_provider_family() not in _OPTIMIZER_OCR_PROVIDER_FAMILIES:
            raise ValueError("Optimizer OCR Provider must support Responses- or Chat-compatible vision inputs.")
        self.interpreter.validate(label="Interpreter")
        self.normalizer.validate(label="Normalizer")
        self.corpus_builder_embeddings.validate(label="Corpus Builder Embeddings")
        self.optimizer_ocr.validate(label="Optimizer OCR")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "llm_shared_provider": self.llm_shared_provider.to_dict(),
            "embeddings_provider": self.embeddings_provider.to_dict(),
            "optimizer_ocr_provider": self.optimizer_ocr_provider.to_dict(),
            "interpreter": self.interpreter.to_dict(),
            "normalizer": self.normalizer.to_dict(),
            "corpus_builder_embeddings": self.corpus_builder_embeddings.to_dict(),
            "optimizer_ocr": self.optimizer_ocr.to_dict(),
        }

    def runtime_settings_for(self, module_key: str, operation: str = "") -> dict[str, Any] | None:
        if module_key == "interpreter":
            return self.interpreter.to_dict()
        if module_key == "normalizer":
            return self.normalizer.to_dict()
        if module_key == "corpus_builder" and operation == "generate_embeddings":
            return self.corpus_builder_embeddings.to_dict()
        if module_key == "optimizer":
            return self.optimizer_ocr.to_dict()
        return None

    def provider_settings_for(self, module_key: str, operation: str = "") -> ProviderEndpointSettings | None:
        if module_key in {"interpreter", "normalizer"}:
            return self.llm_shared_provider
        if module_key == "corpus_builder" and operation == "generate_embeddings":
            return self.embeddings_provider
        if module_key == "optimizer":
            return self.optimizer_ocr_provider
        return None

    def provider_settings_for_target(self, target: str) -> ProviderEndpointSettings:
        if target == "llm_shared":
            return self.llm_shared_provider
        if target == "optimizer_ocr":
            return self.optimizer_ocr_provider
        return self.embeddings_provider

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeSettingsState":
        payload = data if isinstance(data, dict) else {}
        return cls(
            schema_version=coerce_int(payload.get("schema_version", 1), 1, minimum=1),
            llm_shared_provider=ProviderEndpointSettings.from_dict(
                payload.get("llm_shared_provider", {}) or {},
                default_provider_id="openai",
                default_base_url=_DEFAULT_OPENAI_BASE_URL,
            ),
            embeddings_provider=ProviderEndpointSettings.from_dict(
                payload.get("embeddings_provider", {}) or {},
                default_provider_id="openai",
                default_base_url=_DEFAULT_OPENAI_BASE_URL,
            ),
            optimizer_ocr_provider=ProviderEndpointSettings.from_dict(
                payload.get("optimizer_ocr_provider", {}) or {},
                default_provider_id="openai",
                default_base_url=_DEFAULT_OPENAI_BASE_URL,
            ),
            interpreter=LlmRuntimeSettings.from_dict(
                payload.get("interpreter", {}) or {},
                default_model="gpt-5.4",
                default_max_output_tokens=8000,
            ),
            normalizer=LlmRuntimeSettings.from_dict(
                payload.get("normalizer", {}) or {},
                default_model="gpt-5.4-mini",
                default_max_output_tokens=15000,
            ),
            corpus_builder_embeddings=EmbeddingRuntimeSettings.from_dict(
                payload.get("corpus_builder_embeddings", {}) or {},
                default_model="text-embedding-3-small",
            ),
            optimizer_ocr=OptimizerOcrRuntimeSettings.from_dict(
                payload.get("optimizer_ocr", {}) or {},
                default_model="gpt-5.4",
                default_max_output_tokens=15000,
                default_timeout_seconds=120,
            ),
        )
