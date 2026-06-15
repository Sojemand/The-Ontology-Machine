"""Tests fuer processor.py: Verarbeitungsschleife, Cancel, Report."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from types import SimpleNamespace

from ingestion_layer_vision.models import (
    IngestionConfig, OutputFilters,
    InputFileNotFoundError, FileTooLargeError, UnsupportedFormatError,
    PluginError, ExtractResult, atomic_json_write as model_atomic_json_write,
)
from ingestion_layer_vision.plugin_manager import PluginManager
from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.processor import Processor, _RUN_LOCK_NAME


def _mark_output_active(output_dir: Path) -> None:
    (output_dir / _RUN_LOCK_NAME).write_text("occupied", encoding="utf-8")


def _vision_raw_blocks() -> list[dict]:
    return [
        {
            "id": "P1_H1",
            "type": "paragraph",
            "position": {"page": 1, "paragraph_index": 0},
            "value": "Muster GmbH",
            "value_type": "text",
            "formatting": None,
            "confidence": 0.99,
        },
        {
            "id": "P1_F1",
            "type": "paragraph",
            "position": {"page": 1, "paragraph_index": 1},
            "value": "Rechnungsnummer: RE-2026-001",
            "value_type": "text",
            "formatting": None,
            "confidence": 0.98,
        },
        {
            "id": "P2_T1",
            "type": "paragraph",
            "position": {"page": 2, "paragraph_index": 0},
            "value": "Gesamt: 1200,00 EUR",
            "value_type": "text",
            "formatting": None,
            "confidence": 0.97,
        },
    ]


class _VisionPluginManager:
    def get_plugin_for_format(self, ext):
        return "pdf-plugin" if ext == ".pdf" else None

    def invoke(self, plugin_name, file_path, config_override=None):
        del plugin_name, file_path, config_override
        return ExtractResult(
            status="success",
            blocks=_vision_raw_blocks(),
            metadata={"ocr_quality_mode": "best_quality"},
            errors=[],
            processing_time_ms=1,
        )

    def get_manifest(self, plugin_name):
        del plugin_name
        return SimpleNamespace(version="1.0.0", capabilities=["text"])

    def shutdown_workers(self):
        return None

    def kill_all(self):
        return None


def _render_stub_pages(file_path, output_dir, *, asset_key=None, **kwargs):
    del file_path, kwargs
    asset_dir = Path(output_dir) / "page_assets" / str(asset_key or "page_asset")
    asset_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for page in range(1, 3):
        page_path = asset_dir / f"page_{page:03d}.png"
        page_path.write_bytes(b"image-bytes")
        paths.append(str(page_path.resolve()))
    return paths


def _text_blocks(value: str = "ok") -> list[dict]:
    return [
        {
            "id": "B0",
            "type": "paragraph",
            "position": {},
            "value": value,
            "value_type": "text",
            "formatting": None,
            "confidence": 1.0,
        }
    ]

__all__ = [
    "json",
    "pytest",
    "Path",
    "SimpleNamespace",
    "IngestionConfig",
    "OutputFilters",
    "InputFileNotFoundError",
    "FileTooLargeError",
    "UnsupportedFormatError",
    "PluginError",
    "ExtractResult",
    "model_atomic_json_write",
    "PluginManager",
    "InputCatalog",
    "Processor",
    "_mark_output_active",
    "_VisionPluginManager",
    "_render_stub_pages",
    "_text_blocks",
]
