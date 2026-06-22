"""Raw-payload claim collection for numeric/date validation."""
from __future__ import annotations

import html
import math
import re
from typing import Any

from .numeric_claim_parsing import iter_embedded_claims, iter_scalar_claims, record_claim
from .numeric_claim_types import ClaimEvidence

_HTML_TAG_RE = re.compile(r"<[^<>]+>")
_LAYOUT_BOUNDARY_RE = re.compile(r"[\t\n\r\f\v]+")
_LAYOUT_CONTROL_CHARS = {"\t", "\n", "\r", "\f", "\v"}
_STANDALONE_INT_RE = re.compile(r"^\s*(\d{1,4})\s*$")
_TIMECODE = r"\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d{1,3})?"
_FULL_TIMECODE = r"\d{1,2}:\d{2}:\d{2}(?:[\.,]\d{1,3})?"
_TRANSCRIPT_TIMECODE_PATTERNS = (
    re.compile(rf"\[\s*{_TIMECODE}\s*(?:(?:-->|[-\u2013\u2014])\s*{_TIMECODE}\s*)?\]", re.MULTILINE),
    re.compile(rf"(?<![A-Za-z0-9]){_TIMECODE}\s*-->\s*{_TIMECODE}(?![A-Za-z0-9])", re.MULTILINE),
    re.compile(rf"(?<![A-Za-z0-9]){_FULL_TIMECODE}\s*[-\u2013\u2014]\s*{_FULL_TIMECODE}(?![A-Za-z0-9])", re.MULTILINE),
    re.compile(rf"(?<![A-Za-z0-9]){_FULL_TIMECODE}(?![A-Za-z0-9])", re.MULTILINE),
)
_FRONTMATTER_KEY_RE = re.compile(
    r"(?i)\b("
    r"source_url|source_domain|source_name|title|author|published_at|fetched_at|"
    r"url_hash|content_hash|extractor|raw_html_path"
    r")\s*:"
)


def collect_raw_claims(raw_payload: dict[str, Any]) -> dict[str, ClaimEvidence]:
    claims: dict[str, ClaimEvidence] = {}
    reference = raw_payload.get("ocr_reference")
    if isinstance(reference, dict):
        blocks = reference.get("blocks")
        if isinstance(blocks, list):
            for index, block in enumerate(blocks):
                if not isinstance(block, dict):
                    continue
                if _is_edge_page_marker(block.get("value"), index=index, total=len(blocks), raw_payload=raw_payload):
                    continue
                if _is_technical_metadata_block(block.get("value"), raw_payload=raw_payload):
                    continue
                _collect_scalar_claims(
                    block.get("value"),
                    f"ocr_reference.blocks[{index}].value",
                    claims,
                )
    _collect_page_claims(raw_payload.get("pages"), claims)
    _collect_deterministic_extract_claims(raw_payload.get("deterministic_extract"), claims)
    return claims


def _collect_page_claims(pages: Any, claims: dict[str, ClaimEvidence]) -> None:
    if not isinstance(pages, list):
        return
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        blocks = page.get("blocks")
        if isinstance(blocks, list):
            for block_index, block in enumerate(blocks):
                if not isinstance(block, dict):
                    continue
                _collect_scalar_claims(
                    block.get("text"),
                    f"pages[{page_index}].blocks[{block_index}].text",
                    claims,
                )
        _collect_table_claims(page.get("tables"), f"pages[{page_index}].tables", claims)


def _collect_deterministic_extract_claims(payload: Any, claims: dict[str, ClaimEvidence]) -> None:
    if not isinstance(payload, dict):
        return
    _collect_table_claims(payload.get("tables_base"), "deterministic_extract.tables_base", claims)


def _collect_table_claims(tables: Any, field_path: str, claims: dict[str, ClaimEvidence]) -> None:
    if not isinstance(tables, list):
        return
    for table_index, table in enumerate(tables):
        if not isinstance(table, dict):
            continue
        rows = table.get("rows") if isinstance(table.get("rows"), list) else table.get("rows_base")
        if not isinstance(rows, list):
            continue
        for row_index, row in enumerate(rows):
            _collect_row_claims(row, f"{field_path}[{table_index}].rows[{row_index}]", claims)


def _collect_row_claims(row: Any, field_path: str, claims: dict[str, ClaimEvidence]) -> None:
    if isinstance(row, list):
        for col_index, cell in enumerate(row):
            _collect_scalar_claims(cell, f"{field_path}[{col_index}]", claims)
        return
    if not isinstance(row, dict):
        return
    cells = row.get("cells")
    if not isinstance(cells, list):
        return
    for col_index, cell in enumerate(cells):
        if isinstance(cell, dict):
            _collect_scalar_claims(cell.get("value"), f"{field_path}.cells[{col_index}].value", claims)
            continue
        _collect_scalar_claims(cell, f"{field_path}.cells[{col_index}]", claims)


def _collect_scalar_claims(value: Any, field_path: str, claims: dict[str, ClaimEvidence]) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            record_claim(
                claims,
                kind="number",
                raw_value=float(value),
                field_path=field_path,
                display_value=str(value),
                source_kind="raw",
            )
        return
    if isinstance(value, str):
        text = _mask_transcript_timecodes(_strip_html_markup(value))
        for chunk_path, chunk in _iter_layout_chunks(text, field_path):
            _collect_string_claims(chunk, chunk_path, claims)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _collect_scalar_claims(child, f"{field_path}.{key}", claims)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_scalar_claims(child, f"{field_path}[{index}]", claims)


def _collect_string_claims(value: str, field_path: str, claims: dict[str, ClaimEvidence]) -> None:
    for candidate in iter_scalar_claims(value):
        record_claim(
            claims,
            kind=candidate.kind,
            raw_value=candidate.raw_value,
            field_path=field_path,
            display_value=candidate.display_value,
            strength=candidate.strength,
            source_kind="raw",
            quality_flags=candidate.quality_flags,
        )
    for candidate in iter_embedded_claims(value, context_hint=field_path):
        record_claim(
            claims,
            kind=candidate.kind,
            raw_value=candidate.raw_value,
            field_path=field_path,
            display_value=candidate.display_value,
            strength=candidate.strength,
            source_kind="raw",
            quality_flags=candidate.quality_flags,
        )


def _iter_layout_chunks(value: str, field_path: str) -> list[tuple[str, str]]:
    if _LAYOUT_BOUNDARY_RE.search(value) is None:
        return [(field_path, value)]
    chunks: list[tuple[str, str]] = []
    for index, chunk in enumerate(_LAYOUT_BOUNDARY_RE.split(value)):
        stripped = chunk.strip()
        if stripped:
            chunks.append((f"{field_path}.line[{index}]", stripped))
    return chunks


def _strip_html_markup(value: str) -> str:
    if "<" not in value or ">" not in value:
        return value
    stripped = _HTML_TAG_RE.sub(" ", value)
    if stripped == value:
        return value
    return html.unescape(stripped)


def _mask_transcript_timecodes(value: str) -> str:
    text = value
    for pattern in _TRANSCRIPT_TIMECODE_PATTERNS:
        text = pattern.sub(_blank_preserving_layout, text)
    return text


def _blank_preserving_layout(match: re.Match[str]) -> str:
    return "".join(char if char in _LAYOUT_CONTROL_CHARS else " " for char in match.group(0))


def _is_edge_page_marker(value: Any, *, index: int, total: int, raw_payload: dict[str, Any]) -> bool:
    if total <= 1 or index not in {0, total - 1}:
        return False
    if not isinstance(value, str):
        return False
    match = _STANDALONE_INT_RE.match(value)
    if match is None:
        return False
    page_count = _document_page_count(raw_payload)
    if page_count <= 1:
        return False
    return 1 <= int(match.group(1)) <= page_count


def _is_technical_metadata_block(value: Any, *, raw_payload: dict[str, Any]) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if _matches_source_identifier(text, raw_payload):
        return True
    return _looks_like_markdown_frontmatter(text)


def _matches_source_identifier(text: str, raw_payload: dict[str, Any]) -> bool:
    normalized_text = _normalize_source_identifier(text)
    if not normalized_text:
        return False
    for candidate in _source_identifier_candidates(raw_payload):
        normalized_candidate = _normalize_source_identifier(candidate)
        if normalized_candidate and normalized_text in {normalized_candidate, _basename(normalized_candidate)}:
            return True
    return False


def _source_identifier_candidates(raw_payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for container_name in ("source", "context"):
        container = raw_payload.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in (
            "file_name",
            "filename",
            "name",
            "relative_path",
            "file_path",
            "path",
            "source_document_path",
            "page_source_path",
            "document_path",
        ):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.split("::page=", 1)[0])
    return candidates


def _normalize_source_identifier(value: str) -> str:
    return value.strip().strip('"').strip("'").replace("\\", "/").rstrip("/")


def _basename(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _looks_like_markdown_frontmatter(text: str) -> bool:
    if not text.startswith("---"):
        return False
    keys = {match.group(1).lower() for match in _FRONTMATTER_KEY_RE.finditer(text)}
    return len(keys) >= 3


def _document_page_count(raw_payload: dict[str, Any]) -> int:
    candidates: list[Any] = [
        raw_payload.get("page_count"),
        raw_payload.get("document_page_count"),
    ]
    source = raw_payload.get("source")
    if isinstance(source, dict):
        candidates.extend([source.get("page_count"), source.get("document_page_count")])
    context = raw_payload.get("context")
    if isinstance(context, dict):
        candidates.extend([context.get("page_count"), context.get("document_page_count")])
    for candidate in candidates:
        try:
            count = int(candidate)
        except (TypeError, ValueError):
            continue
        if count > 0:
            return count
    return 0


__all__ = ["collect_raw_claims"]
