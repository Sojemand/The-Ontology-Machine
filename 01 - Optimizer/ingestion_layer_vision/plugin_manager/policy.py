"""Built-in extractor policy and manifest defaults."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..extractors import markdown_text, pdf_text
from ..models import PluginManifest
from .types import _InlineRuntime

_INLINE_NAME_TEXT = "markdown-text"
_INLINE_NAME_PDF = "pdf-pdfplumber"
_EXTRACTOR_ORDER = (_INLINE_NAME_TEXT, _INLINE_NAME_PDF)


def _inline_manifest(
    *,
    name: str,
    version: str,
    description: str,
    formats: list[str],
    also_handles: list[str],
    capabilities: list[str],
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version=version,
        description=description,
        author="",
        formats=formats,
        also_handles=also_handles,
        capabilities=capabilities,
        priority=10,
        python_version=">=3.10",
        system_dependencies=[],
        config_schema={},
        config={},
    )


_INLINE_EXTRACTORS: dict[str, _InlineRuntime] = {
    _INLINE_NAME_TEXT: _InlineRuntime(
        manifest=_inline_manifest(
            name=_INLINE_NAME_TEXT,
            version="2.0.0",
            description="Markdown- und Plaintext-Extraktor im Core-Runtime-Pfad",
            formats=[".md", ".txt"],
            also_handles=[".markdown", ".text", ".rst", ".yaml", ".yml", ".toml", ".ini", ".log", ".tex", ".cfg", ".conf", ".env", ".properties"],
            capabilities=["text", "inline_runtime"],
        ),
        extract=markdown_text.extract,
        selftest=markdown_text.selftest,
    ),
    _INLINE_NAME_PDF: _InlineRuntime(
        manifest=_inline_manifest(
            name=_INLINE_NAME_PDF,
            version="2.0.0",
            description="PDF-Extraktor via pdfplumber im Core-Runtime-Pfad",
            formats=[".pdf"],
            also_handles=[],
            capabilities=["text", "tables", "inline_runtime"],
        ),
        extract=pdf_text.extract,
        selftest=pdf_text.selftest,
    ),
}

def build_format_routing(manifests: dict[str, PluginManifest]) -> dict[str, str]:
    routing: dict[str, str] = {}
    for name in _EXTRACTOR_ORDER:
        manifest = manifests.get(name)
        if manifest is None:
            continue
        for fmt in [*manifest.formats, *manifest.also_handles]:
            routing.setdefault(str(fmt).lower(), name)
    return routing
