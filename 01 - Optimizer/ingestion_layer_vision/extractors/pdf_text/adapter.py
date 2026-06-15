"""Runtime adapters for the built-in PDF extractor."""
from __future__ import annotations

from pathlib import Path

from .types import PdfDocumentSnapshot, PdfPageSnapshot, PdfStageError


def ensure_pdfplumber() -> None:
    _import_pdfplumber()


def read_document(path: Path) -> PdfDocumentSnapshot:
    pdfplumber = _import_pdfplumber()
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [_read_page_snapshot(page, index) for index, page in enumerate(pdf.pages, start=1)]
            return PdfDocumentSnapshot(
                page_count=len(pdf.pages),
                pages=pages,
                pdf_version=_read_pdf_version(pdf),
                has_annotations=_read_has_annotations(pdf),
            )
    except PdfStageError:
        raise
    except Exception as exc:
        raise PdfStageError("adapter.open", str(exc)) from exc


def _import_pdfplumber():
    try:
        import pdfplumber
    except ImportError as exc:
        raise PdfStageError("adapter.import", str(exc)) from exc
    return pdfplumber


def _read_page_snapshot(page, page_number: int) -> PdfPageSnapshot:
    return PdfPageSnapshot(
        page_number=page_number,
        text=_read_page_text(page, page_number),
        tables=_read_page_tables(page, page_number),
        has_images=_read_embedded_images(page, page_number),
    )


def _read_page_text(page, page_number: int) -> str:
    try:
        return page.extract_text() or ""
    except Exception as exc:
        raise PdfStageError(f"adapter.page_text[{page_number}]", str(exc)) from exc


def _read_page_tables(page, page_number: int) -> list:
    try:
        return page.extract_tables() or []
    except Exception as exc:
        raise PdfStageError(f"adapter.page_tables[{page_number}]", str(exc)) from exc


def _read_embedded_images(page, page_number: int) -> bool:
    try:
        return bool(page.images)
    except Exception as exc:
        raise PdfStageError(f"adapter.embedded_images[{page_number}]", str(exc)) from exc


def _read_pdf_version(pdf) -> str | None:
    try:
        metadata = pdf.metadata or {}
        return metadata.get("pdf:PDFVersion") or metadata.get("PDFVersion")
    except Exception:
        return None


def _read_has_annotations(pdf) -> bool:
    try:
        return any(bool(page.annots) for page in pdf.pages)
    except Exception:
        return False
