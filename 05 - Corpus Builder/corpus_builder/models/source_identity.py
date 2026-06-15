"""Source-level identity helpers for page or bundle split documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

JsonDict = dict[str, Any]

_PAGE_SUFFIX_PATTERN = re.compile(
    r"^(?P<source>.+?)::page=(?P<page>\d+)(?:-of-(?P<count>\d+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    source_file_path: str
    source_page: int | None
    source_page_count: int | None


@dataclass(frozen=True, slots=True)
class SourceDocumentIdentity:
    source_document_id: str
    source_uri: str
    source_file_id: str | None
    source_artifact_id: str
    ingest_run_id: str
    page_index: int
    page_label: str | None
    materialization_order: int
    page_content_hash: str
    source_content_hash: str


def _mapping(payload: JsonDict, key: str) -> JsonDict:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _context_value(payloads: tuple[JsonDict, ...], *keys: str) -> Any:
    for payload in payloads:
        context = _mapping(payload, "context")
        for key in keys:
            value = context.get(key)
            if value is not None and (not isinstance(value, str) or value.strip()):
                return value
    return None


def _source_value(payloads: tuple[JsonDict, ...], *keys: str) -> Any:
    for payload in payloads:
        source = _mapping(payload, "source")
        for key in keys:
            value = source.get(key)
            if value is not None and (not isinstance(value, str) or value.strip()):
                return value
    return None


def _first_value(payloads: tuple[JsonDict, ...], *keys: str) -> Any:
    for getter in (_source_value, _context_value):
        value = getter(payloads, *keys)
        if value is not None and (not isinstance(value, str) or value.strip()):
            return value
    return None


def parse_source_identity(file_path: str, *payloads: JsonDict) -> SourceIdentity:
    text = str(file_path or "").strip()
    match = _PAGE_SUFFIX_PATTERN.match(text)
    if match:
        return SourceIdentity(
            source_file_path=match.group("source").strip(),
            source_page=_positive_int(match.group("page")),
            source_page_count=_positive_int(match.group("count")),
        )
    return SourceIdentity(
        source_file_path=text,
        source_page=_positive_int(_context_value(payloads, "source_page", "page_number", "page")),
        source_page_count=_positive_int(
            _context_value(payloads, "source_page_count", "document_page_count")
        ),
    )


def build_source_document_identity(
    file_path: str,
    content_hash: str,
    *payloads: JsonDict,
) -> SourceDocumentIdentity:
    source_identity = parse_source_identity(file_path, *payloads)
    source_uri = str(
        _first_value(payloads, "source_uri", "source_file_path")
        or source_identity.source_file_path
        or file_path
    ).strip()
    source_document_id = str(
        _first_value(payloads, "source_document_id")
        or source_uri
    ).strip()
    source_artifact_id = str(
        _first_value(payloads, "source_artifact_id", "artifact_id")
        or source_uri
    ).strip()
    source_file_id_value = _first_value(payloads, "source_file_id", "file_id")
    ingest_run_id = str(_first_value(payloads, "ingest_run_id", "run_id") or "default").strip()
    page_index = _positive_int(_first_value(payloads, "page_index"))
    if page_index is None and source_identity.source_page is not None:
        page_index = max(0, source_identity.source_page - 1)
    if page_index is None:
        page_index = 0
    page_label_value = _first_value(payloads, "page_label")
    page_label = str(page_label_value).strip() if page_label_value is not None else (
        str(source_identity.source_page) if source_identity.source_page is not None else None
    )
    materialization_order = _positive_int(_first_value(payloads, "materialization_order"))
    if materialization_order is None:
        materialization_order = page_index
    source_content_hash = str(_first_value(payloads, "source_content_hash") or content_hash).strip()
    return SourceDocumentIdentity(
        source_document_id=source_document_id,
        source_uri=source_uri,
        source_file_id=str(source_file_id_value).strip() if source_file_id_value is not None else None,
        source_artifact_id=source_artifact_id,
        ingest_run_id=ingest_run_id,
        page_index=page_index,
        page_label=page_label,
        materialization_order=materialization_order,
        page_content_hash=str(content_hash or "").strip(),
        source_content_hash=source_content_hash,
    )


__all__ = ["SourceDocumentIdentity", "SourceIdentity", "build_source_document_identity", "parse_source_identity"]
