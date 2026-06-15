"""Hard invariants for the rtf-reader extractor."""
from __future__ import annotations

from pathlib import Path

from .types import RtfStageError


def validate_source(input_path: str | Path) -> Path:
    source = Path(input_path)
    suffix = source.suffix.lower() or "<ohne Endung>"
    if suffix != ".rtf":
        raise RtfStageError("validation.source", f"RTF-Extraktion nicht unterstuetzt fuer {suffix}")
    if not source.is_file():
        raise RtfStageError("validation.source", f"Quelldatei fehlt: {source}")
    return source
