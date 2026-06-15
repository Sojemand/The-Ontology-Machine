"""Named data carriers for interpreter pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LoadedRequest:
    request: dict[str, Any]
    label: str
    request_path: Path | None
    asset_roots: tuple[Path, ...] = ()


RequestInput = Path | dict[str, Any] | LoadedRequest


@dataclass(frozen=True)
class ProviderCall:
    response_text: str
    provider_name: str
    resolved_model: str
    usage: dict[str, Any]


@dataclass
class DebugBundleState:
    label: str
    request: dict[str, Any] | None = None
    request_path: str | None = None
    message_snapshot: dict[str, Any] | None = None
    raw_provider_text: str | None = None
    parsed_payload: dict[str, Any] | None = None
    persisted_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class BatchPlanItem:
    index: int
    file_path: Path
    output_path: Path
    collision_error: str | None = None
