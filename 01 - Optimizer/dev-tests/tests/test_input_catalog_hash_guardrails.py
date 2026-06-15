from __future__ import annotations

import json
import uuid

import pytest

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import atomic_json_write
from input_catalog_support import write_completed_raw


class TestInputCatalogHashGuardrails:
    def test_completed_raw_outputs_are_bootstrapped(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        output_dir.mkdir()
        state_dir.mkdir()
        source_file = input_dir / "orphan.pdf"
        source_file.write_bytes(b"existing")
        seed_catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert seed_catalog.refresh()
        content_hash = seed_catalog.iter_entries()[0].content_hash
        raw_dir = output_dir / "raw_extracts"
        raw_dir.mkdir()
        atomic_json_write(raw_dir / "orphan.pdf.raw.json", {"schema_version": "optimizer_raw_v2", "source": {"content_hash": content_hash, "ingest_id": str(uuid.uuid4())}})
        catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert catalog.refresh()
        assert catalog.total_count == 0

    def test_path_traversal_and_missing_ingest_id_are_ignored(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        outside_dir = tmp_path / "outside"
        input_dir.mkdir()
        output_dir.mkdir()
        state_dir.mkdir()
        outside_dir.mkdir()
        source_file = input_dir / "existing.pdf"
        source_file.write_bytes(b"existing")
        seed_catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert seed_catalog.refresh()
        content_hash = seed_catalog.iter_entries()[0].content_hash
        raw_dir = output_dir / "raw_extracts"
        raw_dir.mkdir()
        atomic_json_write(raw_dir / "existing.pdf.raw.json", {"schema_version": "optimizer_raw_v2", "source": {"content_hash": content_hash, "ingest_id": "../../outside/escape"}})
        traversal = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert traversal.refresh()
        assert traversal.total_count == 1
        atomic_json_write(raw_dir / "legacy.pdf.raw.json", {"schema_version": "optimizer_raw_v2", "source": {"content_hash": content_hash}})
        legacy = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert legacy.refresh()
        assert legacy.total_count == 1

    def test_scan_excludes_state_and_output_subtrees(self, tmp_path, caplog):
        input_dir = tmp_path / "input"
        state_dir = input_dir / "state"
        output_dir = input_dir / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "keep.txt").write_text("keep", encoding="utf-8")
        (state_dir / "processed_hashes.json").write_text("{broken", encoding="utf-8")
        (state_dir / "ignored.txt").write_text("state", encoding="utf-8")
        (output_dir / "ignored.txt").write_text("output", encoding="utf-8")
        catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert catalog.refresh()
        entries = catalog.iter_entries()
        assert len(entries) == 1
        assert entries[0].filename == "keep.txt"
        assert "processed_hashes.json konnte nicht geladen werden" in caplog.text

    def test_symlink_target_outside_input_is_skipped(self, tmp_path, caplog):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        outside_dir = tmp_path / "outside"
        input_dir.mkdir()
        state_dir.mkdir()
        outside_dir.mkdir()
        outside_file = outside_dir / "escape.txt"
        outside_file.write_text("outside", encoding="utf-8")
        link_path = input_dir / "escape-link.txt"
        try:
            link_path.symlink_to(outside_file)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert catalog.refresh()
        assert catalog.total_count == 0
        assert "ausserhalb des Input-Ordners" in caplog.text

