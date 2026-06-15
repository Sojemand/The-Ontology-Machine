"""Validation helpers for structured document boundaries."""
from __future__ import annotations

from pathlib import Path
from typing import Any

REQUIRED_STRUCTURED_KEYS = ("schema_version", "processing", "classification", "context", "content")
STRUCTURED_OBJECT_SECTIONS = ("processing", "classification", "context", "content")


class DocumentIoValidationError(ValueError):
    """Raised when a structured document or output path violates boundary rules."""


def validate_structured_envelope(structured_doc: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_STRUCTURED_KEYS if key not in structured_doc]
    if missing:
        raise DocumentIoValidationError(f"structured.json unvollstaendig: {', '.join(missing)}")
    invalid = [key for key in STRUCTURED_OBJECT_SECTIONS if not isinstance(structured_doc.get(key), dict)]
    if invalid:
        raise DocumentIoValidationError(f"structured.json Sektionen muessen JSON-Objekte sein: {', '.join(invalid)}")


def validate_structured_file_size(path: Path, max_bytes: int) -> None:
    if max_bytes < 1:
        raise DocumentIoValidationError("max_structured_bytes muss >= 1 sein")
    if path.stat().st_size > max_bytes:
        raise DocumentIoValidationError(f"Structured JSON ueberschreitet max_structured_bytes ({max_bytes} Bytes): {path}")
