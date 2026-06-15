"""Built-in extractor policy and manifest defaults for the Optimizer."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..extractors import markdown_text, pdf_text
from ..models import PluginManifest
from .types import _InlineRuntime

_INLINE_NAME_TEXT = "markdown-text"
_INLINE_NAME_PDF = "pdf-pymupdf"
_PLUGIN_NAME_DOCX = "docx-python"
_PLUGIN_NAME_ODT = "odt-odfpy"
_PLUGIN_NAME_RTF = "rtf-reader"
_PLUGIN_NAME_MAIL_RFC822 = "mail-rfc822"
_PLUGIN_NAME_MAIL_OUTLOOK_MSG = "mail-outlook-msg"
_PLUGIN_NAME_MAIL_OUTLOOK_STORE = "mail-outlook-store"
_EXTRACTOR_ORDER = (
    _INLINE_NAME_TEXT,
    _INLINE_NAME_PDF,
    _PLUGIN_NAME_DOCX,
    _PLUGIN_NAME_ODT,
    _PLUGIN_NAME_RTF,
    _PLUGIN_NAME_MAIL_RFC822,
    _PLUGIN_NAME_MAIL_OUTLOOK_MSG,
    _PLUGIN_NAME_MAIL_OUTLOOK_STORE,
)
_EXPLICIT_FORMATS = {
    _INLINE_NAME_TEXT: [".txt", ".md", ".markdown", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties"],
    _INLINE_NAME_PDF: [".pdf"],
    _PLUGIN_NAME_DOCX: [".docx", ".doc"],
    _PLUGIN_NAME_ODT: [".odt"],
    _PLUGIN_NAME_RTF: [".rtf"],
    _PLUGIN_NAME_MAIL_RFC822: [".eml", ".emlx", ".mbox"],
    _PLUGIN_NAME_MAIL_OUTLOOK_MSG: [".msg", ".oft"],
    _PLUGIN_NAME_MAIL_OUTLOOK_STORE: [".pst", ".ost"],
}


def _inline_manifest(
    *,
    name: str,
    version: str,
    description: str,
    formats: list[str],
    capabilities: list[str],
) -> PluginManifest:
    return PluginManifest(
        name=name,
        version=version,
        description=description,
        author="",
        formats=formats,
        also_handles=[],
        capabilities=capabilities,
        priority=10,
        python_version=">=3.10",
        system_dependencies=[],
        config_schema={},
        config={},
    )


def default_plugin_manifest(name: str) -> PluginManifest:
    return PluginManifest(
        name=name,
        version="1.0.0",
        description=f"Lokaler Dokument-Plugin {name}",
        formats=list(_EXPLICIT_FORMATS[name]),
        also_handles=[],
        capabilities=["text", "tables", "subprocess_runtime"],
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
            version="2.1.0",
            description="Markdown-, Plaintext- und Konfigurations-Extraktor im Core-Runtime-Pfad",
            formats=list(_EXPLICIT_FORMATS[_INLINE_NAME_TEXT]),
            capabilities=["text", "config", "inline_runtime"],
        ),
        extract=markdown_text.extract,
        selftest=markdown_text.selftest,
    ),
    _INLINE_NAME_PDF: _InlineRuntime(
        manifest=_inline_manifest(
            name=_INLINE_NAME_PDF,
            version="3.0.0",
            description="PDF-Extraktor via PyMuPDF im Core-Runtime-Pfad",
            formats=list(_EXPLICIT_FORMATS[_INLINE_NAME_PDF]),
            capabilities=["text", "tables", "inline_runtime"],
        ),
        extract=pdf_text.extract,
        selftest=pdf_text.selftest,
    ),
}


def is_inline_extractor(name: str) -> bool:
    return name in _INLINE_EXTRACTORS


def is_subprocess_extractor(name: str) -> bool:
    return name in {
        _PLUGIN_NAME_DOCX,
        _PLUGIN_NAME_ODT,
        _PLUGIN_NAME_RTF,
        _PLUGIN_NAME_MAIL_RFC822,
        _PLUGIN_NAME_MAIL_OUTLOOK_MSG,
        _PLUGIN_NAME_MAIL_OUTLOOK_STORE,
    }


def build_format_routing(manifests: dict[str, PluginManifest]) -> dict[str, str]:
    routing: dict[str, str] = {}
    for name in _EXTRACTOR_ORDER:
        manifest = manifests.get(name)
        if manifest is None:
            continue
        for fmt in manifest.formats:
            routing[str(fmt).lower()] = name
    return routing


def ordered_manifests(manifests: dict[str, PluginManifest]) -> list[PluginManifest]:
    return [manifests[name] for name in _EXTRACTOR_ORDER if name in manifests]

