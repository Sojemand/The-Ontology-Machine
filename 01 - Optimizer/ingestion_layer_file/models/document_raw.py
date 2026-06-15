"""Raw extract dataclass for file optimizer payloads."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .document_blocks import DataBlock
from .document_metadata import ContextInfo, ExtractionInfo, SourceInfo


@dataclass
class RawExtract:
    source: SourceInfo = field(default_factory=SourceInfo)
    context: ContextInfo = field(default_factory=ContextInfo)
    extraction: ExtractionInfo = field(default_factory=ExtractionInfo)
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_llm_vision: bool = True
    image_paths: list[str] = field(default_factory=list)
    blocks: list[DataBlock] = field(default_factory=list)
    source_blocks: list[DataBlock] = field(default_factory=list)
    page_number: int | None = None
    total_pages: int | None = None

    def to_dict(self) -> dict[str, Any]:
        from .raw_workflow import raw_extract_to_dict

        return raw_extract_to_dict(self)
