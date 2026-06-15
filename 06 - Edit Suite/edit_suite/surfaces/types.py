"""Generic surface datatypes for the Edit Suite."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DraftState:
    surface_id: str
    value: dict[str, Any]
    dirty: bool = False
    message: str = ""


@dataclass(frozen=True)
class SurfaceModel:
    surface_id: str
    label: str
    kind: str
    editable: bool
    editor_kind: str
    descriptor: dict[str, Any]
    value: dict[str, Any]
    draft: dict[str, Any]
    operation_links: tuple[dict[str, Any], ...]
    dirty: bool = False
    message: str = ""
    load_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "label": self.label,
            "kind": self.kind,
            "editable": self.editable,
            "editor_kind": self.editor_kind,
            "descriptor": self.descriptor,
            "value": self.value,
            "draft": self.draft,
            "operation_links": list(self.operation_links),
            "dirty": self.dirty,
            "message": self.message,
            "load_error": self.load_error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SurfaceModel":
        return cls(
            surface_id=str(payload.get("surface_id") or ""),
            label=str(payload.get("label") or ""),
            kind=str(payload.get("kind") or ""),
            editable=bool(payload.get("editable")),
            editor_kind=str(payload.get("editor_kind") or "readonly"),
            descriptor=dict(payload.get("descriptor") or {}),
            value=dict(payload.get("value") or {}),
            draft=dict(payload.get("draft") or {}),
            operation_links=tuple(item for item in payload.get("operation_links", ()) if isinstance(item, dict)),
            dirty=bool(payload.get("dirty")),
            message=str(payload.get("message") or ""),
            load_error=str(payload.get("load_error") or ""),
        )


@dataclass(frozen=True)
class SummaryCardModel:
    card_id: str
    label: str
    body: str
    lines: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"card_id": self.card_id, "label": self.label, "body": self.body, "lines": list(self.lines)}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SummaryCardModel":
        return cls(
            card_id=str(payload.get("card_id") or ""),
            label=str(payload.get("label") or ""),
            body=str(payload.get("body") or ""),
            lines=tuple(str(item) for item in payload.get("lines", ()) if isinstance(item, (str, int, float, bool))),
        )


@dataclass(frozen=True)
class SectionModel:
    name: str
    label: str
    headline: str
    body: str
    summary_cards: tuple[SummaryCardModel, ...] = ()
    surfaces: tuple[SurfaceModel, ...] = ()


@dataclass(frozen=True)
class ModuleSurfaceBundle:
    source: str
    surfaces: tuple[SurfaceModel, ...]
    module_summary: str = ""
    summary_cards: tuple[SummaryCardModel, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "module_summary": self.module_summary,
            "summary_cards": [card.to_dict() for card in self.summary_cards],
            "surfaces": [surface.to_dict() for surface in self.surfaces],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModuleSurfaceBundle":
        return cls(
            source=str(payload.get("source") or "cache"),
            module_summary=str(payload.get("module_summary") or ""),
            summary_cards=tuple(
                SummaryCardModel.from_dict(item) for item in payload.get("summary_cards", ()) if isinstance(item, dict)
            ),
            surfaces=tuple(SurfaceModel.from_dict(item) for item in payload.get("surfaces", ()) if isinstance(item, dict)),
        )
