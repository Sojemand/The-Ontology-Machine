"""Plugin-facing types for extractor routing and results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginManifest:
    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    formats: list[str] = field(default_factory=list)
    also_handles: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    priority: int = 0
    python_version: str = ">=3.10"
    system_dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginRegistryEntry:
    enabled: bool = True
    installed_at: str = ""
    healthy: bool = True


@dataclass
class ExtractResult:
    status: str = "error"
    blocks: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    processing_time_ms: int = 0
    needs_ocr: bool = False
