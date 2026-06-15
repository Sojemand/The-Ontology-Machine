"""Named document types for validator pipeline boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .coercion import compact_alnum, extract_numeric_candidates, normalize_text


@dataclass(frozen=True)
class PreparedFreeText:
    raw_value: Any
    text: str = ""
    normalized: str = ""
    compact: str = ""
    numeric_candidates: tuple[float, ...] = ()
    is_present: bool = False

    @classmethod
    def from_value(cls, value: Any) -> "PreparedFreeText":
        text = value.strip() if isinstance(value, str) else ""
        normalized = normalize_text(text)
        return cls(
            raw_value=value,
            text=text,
            normalized=normalized,
            compact=compact_alnum(text),
            numeric_candidates=tuple(extract_numeric_candidates(text)),
            is_present=bool(text),
        )


@dataclass(frozen=True)
class StructuredRow:
    index: int
    values: dict[str, Any]


@dataclass(frozen=True)
class StructuredDocument:
    interpreter_profile: str
    payload: dict[str, Any]
    context: dict[str, Any]
    fields: dict[str, Any]
    rows: list[StructuredRow]
    free_text: PreparedFreeText
    file_name: str
    file_path: str
    content_hash: str

    @classmethod
    def from_path(cls, structured_path: Path) -> "StructuredDocument":
        from .structured_io import load_structured_document

        return load_structured_document(Path(structured_path))

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        structured_path: Path | None = None,
    ) -> "StructuredDocument":
        from .structured_io import structured_document_from_dict

        return structured_document_from_dict(data, structured_path=structured_path)
