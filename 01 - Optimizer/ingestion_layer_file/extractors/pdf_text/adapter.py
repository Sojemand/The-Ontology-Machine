"""Runtime adapters for the built-in PDF extractor."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import re

from .types import (
    PdfDocumentSnapshot,
    PdfPageSnapshot,
    PdfStageError,
    PdfTextBlockSnapshot,
    PdfTextLineSnapshot,
)


_WHITESPACE_RE = re.compile(r"[ \t]+")


def ensure_pymupdf() -> None:
    _import_fitz()


def read_document(path: Path) -> PdfDocumentSnapshot:
    fitz = _import_fitz()
    try:
        with fitz.open(str(path)) as pdf:
            pages = [_read_page_snapshot(page, index) for index, page in enumerate(pdf, start=1)]
            return PdfDocumentSnapshot(
                page_count=len(pdf),
                pages=pages,
                pdf_version=_read_pdf_version(pdf),
                has_annotations=_read_has_annotations(pdf),
            )
    except PdfStageError:
        raise
    except Exception as exc:
        raise PdfStageError("adapter.open", str(exc)) from exc


def _import_fitz():
    try:
        import fitz
    except ImportError as exc:
        raise PdfStageError("adapter.import", str(exc)) from exc
    return fitz


def _read_page_snapshot(page, page_number: int) -> PdfPageSnapshot:
    text_blocks, text_lines = _read_page_layout(page, page_number)
    return PdfPageSnapshot(
        page_number=page_number,
        text=_read_page_text(page, page_number),
        text_blocks=text_blocks,
        text_lines=text_lines,
        tables=_read_page_tables(page, page_number),
        has_images=_read_page_images(page, page_number),
    )


def _read_page_text(page, page_number: int) -> str:
    try:
        return page.get_text("text", sort=True) or ""
    except Exception as exc:
        raise PdfStageError(f"adapter.page_text[{page_number}]", str(exc)) from exc


def _read_page_layout(page, page_number: int) -> tuple[list[PdfTextBlockSnapshot], list[PdfTextLineSnapshot]]:
    try:
        payload = page.get_text("dict", sort=True) or {}
    except Exception as exc:
        raise PdfStageError(f"adapter.page_layout[{page_number}]", str(exc)) from exc

    text_blocks: list[PdfTextBlockSnapshot] = []
    text_lines: list[PdfTextLineSnapshot] = []
    for raw_block in payload.get("blocks", []) or []:
        if int(raw_block.get("type") or 0) != 0:
            continue
        block_lines: list[str] = []
        for raw_line in raw_block.get("lines", []) or []:
            line_text = _line_text(raw_line)
            if not line_text:
                continue
            text_lines.append(
                PdfTextLineSnapshot(
                    text=line_text,
                )
            )
            block_lines.append(line_text)
        block_text = "\n".join(block_lines).strip()
        if not block_text:
            continue
        text_blocks.append(
            PdfTextBlockSnapshot(
                text=block_text,
            )
        )
    return text_blocks, text_lines


def _read_page_tables(page, page_number: int) -> list:
    find_tables = getattr(page, "find_tables", None)
    if not callable(find_tables):
        return []
    try:
        with redirect_stdout(io.StringIO()):
            finder = find_tables()
    except Exception as exc:
        raise PdfStageError(f"adapter.page_tables[{page_number}]", str(exc)) from exc
    tables: list = []
    for table in getattr(finder, "tables", []) or []:
        try:
            extracted = table.extract() or []
        except Exception as exc:
            raise PdfStageError(f"adapter.page_tables[{page_number}]", str(exc)) from exc
        if extracted:
            tables.append(extracted)
    return tables


def _read_page_images(page, page_number: int) -> bool:
    try:
        return bool(page.get_images())
    except Exception as exc:
        raise PdfStageError(f"adapter.page_images[{page_number}]", str(exc)) from exc


def _read_pdf_version(pdf) -> str | None:
    try:
        metadata = getattr(pdf, "metadata", {}) or {}
        version = str(metadata.get("format", "") or "").strip()
        if version.upper().startswith("PDF "):
            return version.split(" ", 1)[1].strip() or None
        return version or None
    except Exception:
        return None


def _read_has_annotations(pdf) -> bool:
    try:
        for page in pdf:
            annots = getattr(page, "annots", None)
            if not callable(annots):
                continue
            iterator = annots()
            if iterator is None:
                continue
            try:
                next(iterator)
            except StopIteration:
                continue
            return True
    except Exception:
        return False
    return False


def _line_text(raw_line: dict[str, object]) -> str:
    spans = raw_line.get("spans", []) or []
    text = "".join(str(span.get("text", "") or "") for span in spans if isinstance(span, dict))
    return _normalize_text(text)


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(text or "")).strip()
