"""Filesystem-facing adapter for input walking, hashing and output bootstrap."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from .types import CatalogEntry
from .validation import is_valid_uuid_text, is_within, normalize_hash_value

logger = logging.getLogger(__name__)


def compute_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(file_path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        logger.warning("Hash-Berechnung fehlgeschlagen fuer %s: %s", file_path, exc)
        return ""
    return f"sha256:{digest.hexdigest()}"


def build_catalog_entry(
    file_path: Path,
    stat_result,
    *,
    input_root: Path,
    content_hash: str,
    created: str | None = None,
    modified: str | None = None,
) -> CatalogEntry:
    try:
        resolved_path = Path(file_path).resolve()
    except OSError:
        resolved_path = Path(file_path)
    return CatalogEntry(
        path=resolved_path,
        filename=file_path.name,
        extension=file_path.suffix.lower(),
        size_bytes=stat_result.st_size,
        created=created if created is not None else datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
        modified=modified if modified is not None else datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
        relative_path=file_path.relative_to(input_root).as_posix(),
        content_hash=content_hash,
    )


def completed_output_hash(raw_file: Path) -> str | None:
    try:
        payload = json.loads(Path(raw_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    doc = payload.get("doc", {})
    if not isinstance(doc, dict):
        return None

    content_hash = doc.get("content_hash", "")
    if not isinstance(content_hash, str) or not content_hash:
        return None

    ingest_id = doc.get("ingest_id", "")
    if not isinstance(ingest_id, str) or not is_valid_uuid_text(ingest_id):
        return None

    return normalize_hash_value(content_hash)


def collect_existing_output_hashes(output_dir: Path | None) -> set[str]:
    if not output_dir or not Path(output_dir).exists():
        return set()

    raw_dirs = [Path(output_dir) / "raw_extracts"]
    runs_dir = Path(output_dir) / "runs"
    if runs_dir.exists():
        raw_dirs.extend(path for path in runs_dir.glob("*/raw_extracts"))

    hashes: set[str] = set()
    for raw_dir in raw_dirs:
        if not raw_dir.exists():
            continue
        for raw_file in raw_dir.glob("*.raw.json"):
            normalized = completed_output_hash(raw_file)
            if normalized is not None:
                hashes.add(normalized)
    return hashes


def iter_input_files(
    input_dir: Path | None,
    output_dir: Path | None,
    state_dir: Path | None,
):
    if input_dir is None:
        raise ValueError("_path darf nicht None sein")
    root = Path(input_dir)
    try:
        input_root = root.resolve()
    except OSError:
        input_root = root
    excluded_roots = [
        path.resolve()
        for path in (output_dir, state_dir)
        if path and Path(path).exists()
    ]
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            resolved = file_path.resolve()
        except OSError:
            resolved = file_path
        if not is_within(resolved, input_root):
            logger.warning(
                "Input-Datei ausserhalb des Input-Ordners wird uebersprungen: %s -> %s",
                file_path,
                resolved,
            )
            continue
        if any(is_within(resolved, excluded_root) for excluded_root in excluded_roots):
            continue
        yield file_path
