"""Boundary helpers for loader file input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .types import JsonDict, LoadedBundle
from .validation import default_validation_report, validate_normalized_envelope, validate_structured_envelope

def derive_document_id(path: Path) -> str:
    document_id = path.name
    for suffix in (".structured.normalized.json", ".structured.json", ".json"):
        if document_id.endswith(suffix):
            return document_id[: -len(suffix)]
    return document_id


def _load_json_object(path: Path, *, label: str) -> JsonDict:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} ist kein JSON-Objekt")
    return payload


def _inferred_structured_path(normalized_file: Path) -> Path | None:
    name = normalized_file.name
    if not name.endswith(".structured.normalized.json"):
        return None
    structured_name = name.replace(".structured.normalized.json", ".structured.json")
    local_candidate = normalized_file.with_name(structured_name)
    if local_candidate.exists():
        return local_candidate
    parts = normalized_file.parts
    if "normalized" not in parts:
        return None
    normalized_index = len(parts) - 1 - tuple(reversed(parts)).index("normalized")
    sibling_parts = (*parts[:normalized_index], "structured", *parts[normalized_index + 1 : -1], structured_name)
    sibling_candidate = Path(*sibling_parts)
    return sibling_candidate if sibling_candidate.exists() else None


def load_bundle(
    normalized_path: Path,
    validation_path: Path | None,
    *,
    structured_path: Path | None = None,
    raw_path: Path | None = None,
) -> LoadedBundle:
    normalized_file = Path(normalized_path)
    structured_file = Path(structured_path) if structured_path is not None else None
    if structured_file is None and validation_path is not None:
        structured_file = _inferred_structured_path(normalized_file)
    raw_file = Path(raw_path) if raw_path is not None else None
    document_id = derive_document_id(normalized_file)
    normalized_json = _load_json_object(normalized_file, label="normalized.json")
    validate_normalized_envelope(normalized_json)
    structured_json = _load_json_object(structured_file, label="structured.json") if structured_file else None
    raw_json = _load_json_object(raw_file, label="raw.json") if raw_file else None
    if structured_json is not None:
        validate_structured_envelope(structured_json)

    validation_report = default_validation_report()
    if validation_path is not None:
        validation_report = _load_json_object(Path(validation_path), label="Validator-Sidecar")
    elif structured_json is not None:
        raise ValueError("Validator-Sidecar fehlt fuer structured.json")

    source_payload = normalized_json if isinstance(normalized_json, dict) else structured_json or {}
    fallback_payload = structured_json if isinstance(structured_json, dict) else {}
    source = source_payload.get("source") if isinstance(source_payload.get("source"), dict) else {}
    fallback = fallback_payload.get("source") if isinstance(fallback_payload.get("source"), dict) else {}
    content_hash = (
        source.get("content_hash")
        or fallback.get("content_hash")
        or validation_report.get("content_hash")
        or f"sha256:{hashlib.sha256(normalized_file.read_bytes()).hexdigest()}"
    )
    file_path = (
        source.get("file_path")
        or fallback.get("file_path")
        or str(normalized_file)
    )
    return LoadedBundle(
        document_id=document_id,
        structured_json=structured_json,
        raw_json=raw_json,
        normalized_json=normalized_json,
        validation_report=validation_report,
        content_hash=content_hash,
        file_path=file_path,
    )


__all__ = ["derive_document_id", "load_bundle"]
