from __future__ import annotations

import json
from pathlib import Path

from ingestion_layer_vision.input_catalog import CatalogEntry
from ingestion_layer_vision.models import (
    ExtractResult,
    IngestionConfig,
    raw_extract_to_dict,
)
from ingestion_layer_vision.plugin_manager import PluginManager
from ingestion_layer_vision.processor import Processor

MODULE_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = MODULE_ROOT / "dev-tests" / "corpus"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _build_processor(tmp_path: Path) -> Processor:
    output_dir = tmp_path / "output"
    state_dir = tmp_path / "state"
    output_dir.mkdir()
    state_dir.mkdir()
    config = IngestionConfig(plugin_timeout_seconds=10)
    plugin_mgr = PluginManager(MODULE_ROOT / "plugins", config)
    return Processor(
        config,
        plugin_mgr,
        output_dir=output_dir,
    )


def _normalize_raw(payload: dict, *, normalize_ingest: bool, normalize_hash: bool) -> dict:
    normalized = json.loads(json.dumps(payload))
    source = normalized.get("source", {})
    if "file_path" in source:
        source["file_path"] = "<SOURCE_PATH>"
    if normalize_ingest and source.get("ingest_id"):
        source["ingest_id"] = "<INGEST_ID>"
    if normalize_hash and source.get("content_hash"):
        source["content_hash"] = "<CONTENT_HASH>"
    return normalized


class TestRegressionCorpus:
    def test_markdown_corpus_matches_golden_raw(self, tmp_path):
        processor = _build_processor(tmp_path)
        corpus_dir = CORPUS_ROOT / "markdown_invoice"
        source_path = corpus_dir / "invoice.md"

        processor.process_single(source_path, write_output=True, output_dir=tmp_path / "output")

        actual = _load_json(next((tmp_path / "output" / "raw_extracts").glob("*.raw.json")))
        expected = _load_json(corpus_dir / "expected_raw.json")

        assert _normalize_raw(actual, normalize_ingest=True, normalize_hash=True) == expected

    def test_vision_payload_corpus_matches_golden_raw(self, tmp_path):
        processor = _build_processor(tmp_path)
        corpus_dir = CORPUS_ROOT / "vision_payload"
        payload = _load_json(corpus_dir / "input.json")
        source_path = tmp_path / payload["source_filename"]
        source_path.write_bytes(payload["source_bytes_ascii"].encode("ascii"))
        result = ExtractResult(**payload["result"])
        entry = CatalogEntry(
            path=source_path,
            filename=source_path.name,
            extension=".pdf",
            size_bytes=source_path.stat().st_size,
            created="",
            modified="",
            relative_path=payload["relative_path"],
            content_hash=payload["content_hash"],
        )

        extract = processor._build_extract(
            entry=entry,
            file_path=source_path,
            filename=source_path.name,
            ext=".pdf",
            fmt=payload["format"],
            relative_path=payload["relative_path"],
            size=source_path.stat().st_size,
            result=result,
            plugin_name=payload["plugin_name"],
            blocks=processor._parse_blocks(payload["result"]["blocks"]),
            vision=payload["vision"],
            scan_detected=payload["scan_detected"],
            ocr_was_used=payload["ocr_was_used"],
            image_paths=payload["image_paths"],
            content_hash=payload["content_hash"],
            ingest_id=payload["ingest_id"],
        )

        actual = raw_extract_to_dict(extract)
        expected = _load_json(corpus_dir / "expected_raw.json")

        assert _normalize_raw(actual, normalize_ingest=False, normalize_hash=False) == expected
