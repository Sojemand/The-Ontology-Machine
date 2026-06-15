"""Hard invariants for the docx-python extractor."""
from __future__ import annotations

from pathlib import Path

from .types import WordStageError

_ALLOWED_SUFFIXES = {".docx", ".doc"}


def validate_source(input_path: str | Path) -> Path:
    source = Path(input_path)
    suffix = source.suffix.lower() or "<ohne Endung>"
    if suffix not in _ALLOWED_SUFFIXES:
        raise WordStageError("validation.source", f"Word-Extraktion nicht unterstuetzt fuer {suffix}")
    if not source.is_file():
        raise WordStageError("validation.source", f"Quelldatei fehlt: {source}")
    return source
