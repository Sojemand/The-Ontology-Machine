"""Serialization helpers for structured input documents and normalized output names."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..models.serialization import load_json
from .types import StructuredDocument
from .validation import validate_structured_envelope, validate_structured_file_size

_WINDOWS_PATH_BUDGET = 259
_NORMALIZED_SUFFIXES = (".structured.normalized.json", ".normalized.json", ".json")


def load_structured_document(path: Path, *, max_bytes: int | None = None) -> StructuredDocument:
    if max_bytes is not None:
        validate_structured_file_size(path, max_bytes)
    payload = load_json(path)
    validate_structured_envelope(payload)
    return StructuredDocument(path=path, payload=payload)


def normalized_output_file_name(structured_path: Path) -> str:
    name = structured_path.name
    if name.endswith(".structured.json"):
        return name[:-len(".structured.json")] + ".structured.normalized.json"
    return name + ".normalized.json"


def budget_normalized_output_file_name(parent: Path, structured_path: Path, *, path_budget: int = _WINDOWS_PATH_BUDGET) -> str:
    preferred = normalized_output_file_name(structured_path)
    if len(str(Path(parent) / preferred)) <= path_budget:
        return preferred
    stem, suffix = _split_normalized_name(preferred)
    digest = hashlib.sha1(preferred.encode("utf-8")).hexdigest()[:8]
    truncated = stem or "document"
    candidate = f"{truncated}.{digest}{suffix}"
    while len(str(Path(parent) / candidate)) > path_budget and len(truncated) > 1:
        truncated = truncated[:-1]
        candidate_stem = truncated.strip(" ._-") or "d"
        candidate = f"{candidate_stem}.{digest}{suffix}"
    if len(str(Path(parent) / candidate)) > path_budget:
        raise ValueError(f"normalized_output_path waere zu lang fuer Windows-Pfadbudget ({path_budget} Zeichen): {Path(parent) / preferred}")
    return candidate


def _split_normalized_name(name: str) -> tuple[str, str]:
    for suffix in _NORMALIZED_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)] or "document", suffix
    path = Path(name)
    return path.stem or "document", path.suffix
