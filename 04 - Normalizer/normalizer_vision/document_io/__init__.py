"""Path-stable surface for structured document boundary helpers."""
from __future__ import annotations

from .serialization import budget_normalized_output_file_name, load_structured_document, normalized_output_file_name
from .types import StructuredDocument
from .validation import (
    DocumentIoValidationError,
    REQUIRED_STRUCTURED_KEYS,
    STRUCTURED_OBJECT_SECTIONS,
    validate_structured_envelope,
    validate_structured_file_size,
)

__all__ = [
    "DocumentIoValidationError",
    "REQUIRED_STRUCTURED_KEYS",
    "STRUCTURED_OBJECT_SECTIONS",
    "StructuredDocument",
    "budget_normalized_output_file_name",
    "load_structured_document",
    "normalized_output_file_name",
    "validate_structured_envelope",
    "validate_structured_file_size",
]
