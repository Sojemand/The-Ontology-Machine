"""Text-neutral page attribution helpers for rendered intermediate PDFs."""
from __future__ import annotations

import copy
import re
import unicodedata
from pathlib import Path
from typing import Any

from ..extractors.pdf_text import extract as extract_pdf_text
from ..models import BlockFormatting, BlockPosition, DataBlock, IngestionConfig

_WHITESPACE_RE = re.compile(r"\s+")
_LINE_HYPHEN_RE = re.compile(r"(?<=\w)-\s+(?=\w)")
_DASH_SPACING_RE = re.compile(r"\s*([\u2014\u2013])\s*")
_MAX_REFERENCE_WINDOW = 24
_MIN_REFERENCE_OVERLAP = 16
_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2026": "...",
    }
)


def extract_page_reference_blocks(pdf_path: str | Path, config: IngestionConfig) -> list[DataBlock]:
    payload = extract_pdf_text(pdf_path)
    if payload.get("status") != "success":
        detail = "; ".join(str(item).strip() for item in payload.get("errors", []) if str(item).strip())
        raise RuntimeError(detail or f"PDF-Reextraktion fehlgeschlagen fuer {Path(pdf_path).name}")
    return _parse_blocks(payload.get("blocks", []), config)


def apply_page_attribution(
    source_blocks: list[DataBlock],
    reference_blocks: list[DataBlock],
    *,
    total_pages: int,
) -> list[DataBlock]:
    if total_pages <= 0:
        raise RuntimeError("Page attribution erfordert mindestens eine Seite.")
    if total_pages == 1:
        return [_with_single_page_position(block) for block in source_blocks]
    if all(_has_page_info(block) for block in source_blocks):
        return [copy.deepcopy(block) for block in source_blocks]
    if not reference_blocks:
        raise RuntimeError("Page attribution erfordert Referenzbloecke fuer mehrseitige Dokumente.")

    attributed: list[DataBlock] = []
    cursor = 0
    for block in source_blocks:
        if _has_page_info(block):
            attributed.append(copy.deepcopy(block))
            continue
        match = _match_reference_window(block, reference_blocks, cursor)
        if match is None:
            raise RuntimeError(
                f"File-Pfad fail-closed: native page attribution nicht deterministisch fuer Block {block.id!r}."
            )
        start_index, end_index = match
        cursor = _next_cursor(block, reference_blocks, start_index, end_index)
        attributed.append(_apply_reference_window(block, reference_blocks[start_index : end_index + 1]))
    return attributed


def _parse_blocks(raw_blocks: list[dict[str, Any]], config: IngestionConfig) -> list[DataBlock]:
    blocks: list[DataBlock] = []
    for index, raw_block in enumerate(raw_blocks[: config.max_blocks_per_file]):
        pos_data = raw_block.get("position", {}) if isinstance(raw_block, dict) else {}
        fmt_data = raw_block.get("formatting") if isinstance(raw_block, dict) else None
        position = BlockPosition(
            page=pos_data.get("page") if isinstance(pos_data, dict) else None,
            paragraph_index=pos_data.get("paragraph_index") if isinstance(pos_data, dict) else None,
            table_index=pos_data.get("table_index") if isinstance(pos_data, dict) else None,
            row=pos_data.get("row") if isinstance(pos_data, dict) else None,
            col=pos_data.get("col") if isinstance(pos_data, dict) else None,
        )
        formatting = None
        if isinstance(fmt_data, dict):
            merged_with = fmt_data.get("merged_with")
            if merged_with is None and fmt_data.get("merged_range"):
                merged_with = [fmt_data.get("merged_range")]
            formatting = BlockFormatting(
                bold=fmt_data.get("bold"),
                font_size=fmt_data.get("font_size"),
                merged_with=merged_with,
            )
        blocks.append(
            DataBlock(
                id=str(raw_block.get("id", f"B{index}")) if isinstance(raw_block, dict) else f"B{index}",
                type=str(raw_block.get("type", "paragraph")) if isinstance(raw_block, dict) else "paragraph",
                position=position,
                value=raw_block.get("value") if isinstance(raw_block, dict) else None,
                value_type=str(raw_block.get("value_type", "text")) if isinstance(raw_block, dict) else "text",
                formatting=formatting,
            )
        )
    return blocks


def _with_single_page_position(block: DataBlock) -> DataBlock:
    cloned = copy.deepcopy(block)
    if cloned.position.page is None:
        cloned.position.page = 1
    return cloned


def _has_page_info(block: DataBlock) -> bool:
    if block.page_span:
        return True
    return getattr(block.position, "page", None) is not None


def _match_reference_window(
    block: DataBlock,
    reference_blocks: list[DataBlock],
    start_index: int,
) -> tuple[int, int] | None:
    if start_index >= len(reference_blocks):
        return None
    source_text = _normalize_text(block.value)
    if not source_text:
        return start_index, start_index
    max_start_index = min(len(reference_blocks), start_index + _MAX_REFERENCE_WINDOW)
    for candidate_start in range(start_index, max_start_index):
        accumulated: list[str] = []
        for end_index in range(candidate_start, min(len(reference_blocks), candidate_start + _MAX_REFERENCE_WINDOW)):
            reference_text = _normalize_text(reference_blocks[end_index].value)
            if reference_text:
                accumulated.append(reference_text)
            candidate = " ".join(accumulated).strip()
            if not candidate:
                continue
            if candidate == source_text:
                return candidate_start, end_index
            if source_text in candidate:
                return candidate_start, end_index
            if source_text.startswith(candidate) or _candidate_suffix_starts_source(source_text, candidate):
                continue
            break
    return None


def _candidate_suffix_starts_source(source_text: str, candidate: str) -> bool:
    max_overlap = min(len(source_text), len(candidate))
    for size in range(max_overlap, _MIN_REFERENCE_OVERLAP - 1, -1):
        if candidate[-size:] == source_text[:size]:
            return True
    return False


def _next_cursor(block: DataBlock, reference_blocks: list[DataBlock], start_index: int, end_index: int) -> int:
    if start_index != end_index:
        return end_index
    source_text = _normalize_text(block.value)
    if source_text and start_index == end_index:
        reference_text = _normalize_text(reference_blocks[start_index].value)
        if reference_text and source_text in reference_text and reference_text != source_text:
            return start_index
    return end_index + 1


def _apply_reference_window(block: DataBlock, reference_window: list[DataBlock]) -> DataBlock:
    cloned = copy.deepcopy(block)
    first = reference_window[0]
    pages = [int(item.position.page) for item in reference_window if getattr(item.position, "page", None) is not None]
    if not pages:
        raise RuntimeError(f"Page attribution ohne Seitenangabe fuer Block {block.id!r}.")
    unique_pages = sorted(dict.fromkeys(pages))
    cloned.position.page = unique_pages[0]
    cloned.position.paragraph_index = first.position.paragraph_index
    cloned.position.table_index = first.position.table_index
    cloned.position.row = first.position.row
    cloned.position.col = first.position.col
    if unique_pages[0] == unique_pages[-1]:
        cloned.page_span = None
    else:
        cloned.page_span = unique_pages
    return cloned


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_PUNCTUATION_TRANSLATION)
    text = _LINE_HYPHEN_RE.sub("-", text)
    text = _DASH_SPACING_RE.sub(r"\1", text)
    return _WHITESPACE_RE.sub(" ", text).strip()
