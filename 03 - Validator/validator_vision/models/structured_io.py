"""Structured-document read boundaries for validator serialization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .types import PreparedFreeText, StructuredDocument, StructuredRow

MAX_JSON_BYTES = 16 * 1024 * 1024


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    data = _loads_json_object(_read_json_bytes(path, label=label), path=path, label=label)
    if not isinstance(data, dict):
        raise ValueError(f"{label} ist kein JSON-Objekt: {path}")
    return data


def load_structured_document(path: Path) -> StructuredDocument:
    structured_path = Path(path)
    raw = _read_json_bytes(structured_path, label="Structured JSON")
    data = _loads_json_object(raw, path=structured_path, label="Structured JSON")
    if not isinstance(data, dict):
        raise ValueError(f"Structured JSON ist kein JSON-Objekt: {structured_path}")
    fallback_content_hash = ""
    if not _has_source_content_hash(data.get("source")):
        fallback_content_hash = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    return structured_document_from_dict(
        data,
        structured_path=structured_path,
        fallback_content_hash=fallback_content_hash,
    )


def structured_document_from_dict(
    data: dict[str, Any],
    *,
    structured_path: Path | None = None,
    fallback_content_hash: str = "",
) -> StructuredDocument:
    if not isinstance(data, dict):
        if structured_path is None:
            raise ValueError("Structured JSON ist kein Objekt.")
        raise ValueError(f"Structured JSON ist kein Objekt: {structured_path}")

    content = _object_section(data, "content", structured_path=structured_path)
    context = _object_section(data, "context", structured_path=structured_path)
    source = _object_section(data, "source", structured_path=structured_path)
    processing = _object_section(data, "processing", structured_path=structured_path)

    interpreter_profile = str(processing.get("interpreter_profile") or "").strip()
    if not interpreter_profile:
        if structured_path is None:
            raise ValueError("Structured JSON fehlt processing.interpreter_profile.")
        raise ValueError(
            f"Structured JSON fehlt processing.interpreter_profile: {structured_path}"
        )

    fields = content.get("fields", {})
    if fields is None:
        fields = {}
    if not isinstance(fields, dict):
        raise ValueError(_field_error("content.fields muss ein JSON-Objekt sein", structured_path))

    rows: list[StructuredRow] = []
    raw_rows = content.get("rows", [])
    if raw_rows is None:
        raw_rows = []
    if not isinstance(raw_rows, list):
        raise ValueError(_field_error("content.rows muss eine Liste sein", structured_path))
    for index, row in enumerate(raw_rows):
        if isinstance(row, dict):
            rows.append(StructuredRow(index=index, values=row))

    return StructuredDocument(
        interpreter_profile=interpreter_profile,
        payload=data,
        context=context,
        fields=fields,
        rows=rows,
        free_text=PreparedFreeText.from_value(content.get("free_text")),
        file_name=_source_file_name(source, structured_path),
        file_path=str(structured_path.resolve()) if structured_path is not None else "",
        content_hash=_content_hash(source, structured_path, fallback_content_hash=fallback_content_hash),
    )


def _object_section(data: dict[str, Any], name: str, *, structured_path: Path | None) -> dict[str, Any]:
    value = data.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(_field_error(f"{name} muss ein JSON-Objekt sein", structured_path))
    return value


def _field_error(message: str, structured_path: Path | None) -> str:
    if structured_path is None:
        return message
    return f"{message}: {structured_path}"


def _source_file_name(source: dict[str, Any], structured_path: Path | None) -> str:
    file_name = source.get("file_name")
    if isinstance(file_name, str) and file_name.strip():
        return file_name
    if structured_path is None:
        return "document"
    name = structured_path.name
    if name.endswith(".structured.json"):
        return name[: -len(".structured.json")]
    return structured_path.name


def _content_hash(source: dict[str, Any], structured_path: Path | None, *, fallback_content_hash: str = "") -> str:
    content_hash = source.get("content_hash")
    if isinstance(content_hash, str) and content_hash.strip():
        return content_hash
    if fallback_content_hash:
        return fallback_content_hash
    if structured_path is None or not structured_path.exists():
        return ""
    return f"sha256:{_sha256_file(structured_path)}"


def _has_source_content_hash(source: Any) -> bool:
    return isinstance(source, dict) and isinstance(source.get("content_hash"), str) and bool(source["content_hash"].strip())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_oversized_json(path: Path, *, label: str) -> None:
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size > MAX_JSON_BYTES:
        raise ValueError(f"{label} ist zu gross: {path} ({size} Bytes, Limit {MAX_JSON_BYTES})")


def _read_json_bytes(path: Path, *, label: str) -> bytes:
    _reject_oversized_json(path, label=label)
    return path.read_bytes()


def _loads_json_object(raw: bytes, *, path: Path, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(f"{exc.msg}: {path}", exc.doc, exc.pos) from exc
