from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ingestion_layer_vision.input_catalog import CatalogEntry
from ingestion_layer_vision.models import ExtractResult, IngestionConfig
from ingestion_layer_vision.processor import Processor


VALID_HEX_64 = "a" * 64
VALID_HASH = f"sha256:{VALID_HEX_64}"


class StubPluginManager:
    """Minimal plugin manager that satisfies Processor.__init__."""

    def get_plugin_for_format(self, ext):
        return "stub-plugin"

    def invoke(self, plugin_name, file_path, config_override=None):
        return ExtractResult(
            status="success",
            blocks=[],
            metadata={},
            errors=[],
            processing_time_ms=0,
        )

    def get_manifest(self, plugin_name):
        return SimpleNamespace(version="0.0.1", capabilities=["text"])

    def shutdown_workers(self):
        return None

    def kill_all(self):
        return None


def make_processor(tmp_path: Path) -> Processor:
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return Processor(
        config=IngestionConfig(),
        plugin_mgr=StubPluginManager(),
        output_dir=output_dir,
    )


def catalog_entry(path: Path, *, content_hash: str) -> CatalogEntry:
    return CatalogEntry(
        path=path,
        filename=path.name,
        extension=path.suffix.lower(),
        size_bytes=path.stat().st_size,
        created="",
        modified="",
        relative_path=path.name,
        content_hash=content_hash,
    )
