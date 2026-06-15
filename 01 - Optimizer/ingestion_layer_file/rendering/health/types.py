"""Typed contracts for rendering runtime health checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

RendererProbeFn = Callable[[], tuple[bool, str]]


@dataclass(frozen=True)
class RendererRuntimeProbe:
    name: str
    run: RendererProbeFn
    kind: str = "runtime"
    required: bool = True


@dataclass(frozen=True)
class RendererDependencyCheck:
    name: str
    kind: str
    required: bool
    healthy: bool
    detail: str

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "required": self.required,
            "healthy": self.healthy,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class RendererHealthSummary:
    healthy: bool
    detail: str
