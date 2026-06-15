"""Named carriers for the normalizer workflow stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ModelClient(Protocol):
    def generate(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
        thinking_effort: str,
    ) -> str:
        ...

    def is_available(self) -> bool:
        ...

    @property
    def provider_name(self) -> str:
        ...


@dataclass(frozen=True)
class ParsedModelOutput:
    schema_version: str | None
    processing: dict[str, Any]
    classification: dict[str, Any]
    context: dict[str, Any]
    content: dict[str, Any]


@dataclass(frozen=True)
class NormalizedContent:
    structure: dict[str, Any]
    fields: dict[str, Any]
    rows: list[dict[str, Any]]
    free_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure": self.structure,
            "fields": self.fields,
            "rows": self.rows,
            "free_text": self.free_text,
        }


@dataclass(frozen=True)
class NormalizedEnvelope:
    schema_version: str
    processing: dict[str, Any]
    classification: dict[str, Any]
    context: dict[str, Any]
    content: NormalizedContent
    projection: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "processing": self.processing,
            "classification": self.classification,
            "context": self.context,
            "content": self.content.to_dict(),
            "projection": self.projection,
        }
