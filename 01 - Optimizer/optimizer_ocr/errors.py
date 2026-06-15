"""Controlled Optimizer OCR error types."""

from __future__ import annotations


class LlmOcrError(RuntimeError):
    """Base class for controlled LLM-OCR failures."""


class LlmOcrConfigurationError(LlmOcrError):
    """Raised when optimizer_ocr provider/model/credential settings are incomplete."""


class LlmOcrResponseError(LlmOcrError):
    """Raised when the provider response or model JSON violates the OCR contract."""
