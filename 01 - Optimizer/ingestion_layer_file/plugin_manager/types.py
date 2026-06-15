"""Shared plugin manager runtime types."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..models import PluginManifest


@dataclass(frozen=True)
class _InlineRuntime:
    manifest: PluginManifest
    extract: Callable[[str | Path, dict[str, Any] | None], dict[str, Any]]
    selftest: Callable[[], dict[str, Any]]
