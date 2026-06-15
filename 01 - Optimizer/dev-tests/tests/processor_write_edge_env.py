from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

from ingestion_layer_vision.models import (
    ContextInfo,
    ExtractResult,
    ExtractionInfo,
    IngestionConfig,
    RawExtract,
    SourceInfo,
)
from ingestion_layer_vision.processor import Processor


class StubPluginManager:
    def get_plugin_for_format(self, ext):
        return None

    def invoke(self, *a, **kw):
        return ExtractResult(status="error", errors=["stub"])

    def get_manifest(self, name):
        return SimpleNamespace(version="1.0.0", capabilities=[])

    def shutdown_workers(self):
        pass

    def kill_all(self):
        pass


def minimal_extract(content_hash="sha256:" + "ab" * 32, filename="test.pdf", ingest_id=None):
    return RawExtract(
        source=SourceInfo(
            ingest_id=ingest_id or str(uuid.uuid4()),
            owner_id=None,
            path="/tmp/test.pdf",
            filename=filename,
            format="pdf",
            size_bytes=1000,
            created="",
            modified="",
            content_hash=content_hash,
            relative_path=filename,
        ),
        context=ContextInfo(),
        extraction=ExtractionInfo(
            plugin_name="test",
            plugin_version="1.0",
            processing_time_ms=1,
            block_count=0,
            ocr_used=False,
        ),
        needs_llm_vision=False,
        image_paths=[],
        blocks=[],
    )


def make_processor(tmp_path: Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = Processor(IngestionConfig(), StubPluginManager(), output_dir=output_dir)
    proc._extracts_dir = output_dir / "raw_extracts"
    proc._extracts_dir.mkdir(parents=True, exist_ok=True)
    return proc
