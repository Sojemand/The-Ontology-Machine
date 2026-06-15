"""Read-only boundary helpers for validator workflow inputs."""
from __future__ import annotations

from pathlib import Path

from ..models.types import StructuredDocument

MAX_BATCH_DOCUMENTS = 5000


def normalize_path(path: Path | str) -> Path:
    return Path(path)


def load_structured_document(structured_path: Path | str) -> StructuredDocument:
    return StructuredDocument.from_path(normalize_path(structured_path))


def discover_structured_documents(structured_dir: Path | str) -> list[Path]:
    documents: list[Path] = []
    for path in normalize_path(structured_dir).rglob("*.structured.json"):
        documents.append(path)
        if len(documents) > MAX_BATCH_DOCUMENTS:
            raise ValueError(
                f"Zu viele Structured-Dokumente: mehr als {MAX_BATCH_DOCUMENTS} "
                f"(Limit {MAX_BATCH_DOCUMENTS})"
            )
    return sorted(documents)
