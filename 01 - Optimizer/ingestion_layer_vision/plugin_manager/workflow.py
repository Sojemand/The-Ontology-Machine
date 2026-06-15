"""Workflow orchestration for the static Vision extractor registry."""
from __future__ import annotations

import logging
from pathlib import Path

from ..models import ExtractResult, PluginRegistryEntry
from . import policy

logger = logging.getLogger(__name__)


def load_manifests(registry) -> None:
    for name in (policy._INLINE_NAME_TEXT, policy._INLINE_NAME_PDF):
        registry._manifests[name] = policy._INLINE_EXTRACTORS[name].manifest
        registry.plugins[name] = PluginRegistryEntry(enabled=True, installed_at="", healthy=True)
    registry.format_routing = policy.build_format_routing(registry._manifests)


def invoke(
    registry,
    name: str,
    file_path: Path,
    config_override: dict | None = None,
    *,
    worker_startup_config: dict | None = None,
) -> ExtractResult:
    del worker_startup_config
    if name in policy._INLINE_EXTRACTORS:
        return registry._invoke_inline(name, file_path, config_override)
    return ExtractResult(status="error", errors=[f"Extractor {name} nicht gefunden"])


def invoke_inline(registry, name: str, file_path: Path, config_override: dict | None = None) -> ExtractResult:
    runtime = policy._INLINE_EXTRACTORS[name]
    try:
        payload = runtime.extract(file_path, config_override or runtime.manifest.config)
    except Exception as exc:
        logger.warning("Inline extractor %s failed for %s: %s", name, file_path, exc)
        return ExtractResult(status="error", errors=[f"Inline-Extractor {name} fehlgeschlagen: {exc}"])
    return registry._parse_result(payload)


def selftest(registry, name: str, *, timeout_seconds: int | None = None) -> tuple[bool, str]:
    del registry, timeout_seconds
    if name not in policy._INLINE_EXTRACTORS:
        return False, f"Extractor {name} nicht gefunden"
    data = policy._INLINE_EXTRACTORS[name].selftest()
    if data.get("status") == "ok":
        return True, f"OK (v{data.get('version', '?')})"
    return False, data.get("message") or data.get("error") or "Unbekannter Fehler"
