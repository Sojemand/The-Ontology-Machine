"""Runtime and byte-decoding adapters for the rtf-reader extractor."""
from __future__ import annotations

from pathlib import Path

from .types import RtfDocumentSnapshot, RtfStageError


def ensure_striprtf() -> None:
    _import_runtime()


def load_document_snapshot(source: Path) -> RtfDocumentSnapshot:
    rtf_to_text = _import_runtime()
    raw_bytes = _read_source_bytes(source)
    rtf_content = _decode_rtf_bytes(raw_bytes)
    plain_text = _convert_to_text(rtf_to_text, rtf_content)
    return RtfDocumentSnapshot(
        plain_text=plain_text,
        line_count=len(plain_text.split("\n")),
    )


def _import_runtime():
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError as exc:
        raise RtfStageError("adapter.runtime", str(exc)) from exc
    return rtf_to_text


def _read_source_bytes(source: Path) -> bytes:
    try:
        return source.read_bytes()
    except Exception as exc:
        raise RtfStageError("adapter.read", str(exc)) from exc


def _decode_rtf_bytes(raw_bytes: bytes) -> str:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _convert_to_text(rtf_to_text, rtf_content: str) -> str:
    try:
        return rtf_to_text(rtf_content)
    except Exception as exc:
        raise RtfStageError("adapter.convert", str(exc)) from exc
