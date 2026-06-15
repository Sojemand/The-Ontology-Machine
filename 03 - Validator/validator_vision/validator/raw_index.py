"""Raw-input lookup helpers for validator workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models.structured_io import read_json_object
from ..models.types import StructuredDocument

MAX_RAW_INDEX_FILES = 5000


@dataclass
class RawIndex:
    by_content_hash: dict[str, list[Path]] = field(default_factory=dict)
    by_file_name: dict[str, list[Path]] = field(default_factory=dict)
    skipped_files: list[str] = field(default_factory=list)


def load_raw_payload(raw_path: Path | str) -> dict:
    return read_json_object(Path(raw_path), label="Raw JSON")


def build_raw_index(raw_root: Path | str) -> RawIndex:
    root = Path(raw_root)
    index = RawIndex()
    raw_paths: list[Path] = []
    for raw_path in root.rglob("*.raw.json"):
        raw_paths.append(raw_path)
        if len(raw_paths) > MAX_RAW_INDEX_FILES:
            raise ValueError(f"Zu viele Raw-Dateien: mehr als {MAX_RAW_INDEX_FILES} (Limit {MAX_RAW_INDEX_FILES})")
    for raw_path in sorted(raw_paths):
        try:
            payload = load_raw_payload(raw_path)
        except Exception as exc:
            index.skipped_files.append(f"{raw_path}: {exc}")
            continue
        source = payload.get("source") or payload.get("doc")
        if not isinstance(source, dict):
            continue
        content_hash = str(source.get("content_hash") or "").strip()
        file_name = str(source.get("file_name") or source.get("filename") or "").strip()
        if content_hash:
            index.by_content_hash.setdefault(content_hash, []).append(raw_path)
        if file_name:
            index.by_file_name.setdefault(file_name, []).append(raw_path)
    return index


def resolve_raw_path(
    document: StructuredDocument,
    *,
    raw_path: Path | str | None = None,
    raw_root: Path | str | None = None,
    raw_index: RawIndex | None = None,
) -> Path:
    if raw_path is not None:
        return Path(raw_path)
    if raw_root is None:
        raise ValueError("Validator benoetigt Raw-Evidence: raw_path oder raw_root fehlt.")

    index = raw_index or build_raw_index(raw_root)
    if document.content_hash:
        candidates = index.by_content_hash.get(document.content_hash, [])
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(f"Mehrdeutiges Raw fuer content_hash {document.content_hash}: {len(candidates)} Treffer")
    if document.file_name:
        candidates = index.by_file_name.get(document.file_name, [])
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(f"Mehrdeutiges Raw fuer file_name {document.file_name}: {len(candidates)} Treffer")
    skipped = f" Uebersprungene Raw-Dateien: {len(index.skipped_files)}." if index.skipped_files else ""
    raise ValueError(
        "Raw-Evidence konnte fuer das Structured-Dokument nicht eindeutig aufgeloest werden."
        + skipped
    )


__all__ = ["RawIndex", "build_raw_index", "load_raw_payload", "resolve_raw_path"]
