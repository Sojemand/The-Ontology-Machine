from __future__ import annotations

from pathlib import Path


def _is_runtime_validation_input(path: str) -> bool:
    candidate = Path(path)
    return candidate.name.endswith(".structured.json") and candidate.parent.name == "structured" and candidate.parent.parent.name.startswith("d.")


def _is_runtime_structured_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.name.endswith(".structured.json") and candidate.parent.name == "structured" and candidate.parent.parent.name.startswith("d.")


def _is_runtime_normalized_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.name.endswith(".structured.normalized.json") and candidate.parent.name == "normalized" and candidate.parent.parent.name.startswith("d.")
