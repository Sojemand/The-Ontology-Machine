"""Hard invariants for the odt-odfpy extractor."""
from __future__ import annotations

from pathlib import Path

from .types import OdtStageError


def validate_source(input_path: str | Path) -> Path:
    source = Path(input_path)
    suffix = source.suffix.lower() or "<ohne Endung>"
    if suffix != ".odt":
        raise OdtStageError("validation.source", f"OpenDocument-Extraktion nicht unterstuetzt fuer {suffix}")
    if not source.is_file():
        raise OdtStageError("validation.source", f"Quelldatei fehlt: {source}")
    return source
