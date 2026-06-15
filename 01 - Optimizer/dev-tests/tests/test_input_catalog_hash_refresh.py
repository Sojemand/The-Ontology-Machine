from __future__ import annotations

import json

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import atomic_json_write
from input_catalog_support import write_completed_raw


class TestInputCatalogHashRefresh:
    def test_duplicate_and_processed_hashes_are_skipped(self, tmp_path):
        input_dir = tmp_path / "dup-input"
        state_dir = tmp_path / "dup-state"
        input_dir.mkdir()
        state_dir.mkdir()
        (input_dir / "copy_a.txt").write_text("same", encoding="utf-8")
        (input_dir / "copy_b.txt").write_text("same", encoding="utf-8")
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert catalog.refresh()
        assert catalog.total_count == 1
        assert catalog.skipped_duplicate_count == 1

        processed_input = tmp_path / "processed-input"
        processed_state = tmp_path / "processed-state"
        processed_input.mkdir()
        processed_state.mkdir()
        (processed_input / "done.txt").write_text("already done", encoding="utf-8")
        processed_catalog = InputCatalog(processed_input, state_dir=processed_state)
        assert processed_catalog.refresh()
        processed_hash = processed_catalog.iter_entries()[0].content_hash
        processed_catalog.mark_processed_hash(processed_hash)
        second = InputCatalog(processed_input, state_dir=processed_state)
        assert second.refresh()
        assert second.total_count == 0
        assert second.skipped_processed_count == 1

    def test_bootstraps_hashes_from_existing_output_and_runs(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        output_dir.mkdir()
        state_dir.mkdir()
        source_file = input_dir / "existing.pdf"
        source_file.write_bytes(b"existing")
        seed_catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert seed_catalog.refresh()
        content_hash = seed_catalog.iter_entries()[0].content_hash
        write_completed_raw(output_dir, "existing.pdf", content_hash)
        write_completed_raw(output_dir / "runs" / "run-001", "nested.pdf", content_hash)
        catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert catalog.refresh()
        assert catalog.total_count == 0
        assert catalog.skipped_processed_count == 1

    def test_reset_hashes_stays_empty_even_with_existing_output(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        output_dir.mkdir()
        state_dir.mkdir()
        source_file = input_dir / "existing.pdf"
        source_file.write_bytes(b"existing")
        seed_catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert seed_catalog.refresh()
        content_hash = seed_catalog.iter_entries()[0].content_hash
        write_completed_raw(output_dir, "existing.pdf", content_hash)
        catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert catalog.refresh()
        assert catalog.clear_processed_hashes() == 1
        refreshed = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert refreshed.refresh()
        assert refreshed.total_count == 1
        assert refreshed.skipped_processed_count == 0

    def test_processed_hash_state_bootstrap_and_merge(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        output_dir.mkdir()
        state_dir.mkdir()
        source_file = input_dir / "existing.pdf"
        source_file.write_bytes(b"existing")
        seed_catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert seed_catalog.refresh()
        content_hash = seed_catalog.iter_entries()[0].content_hash
        write_completed_raw(output_dir, "existing.pdf", content_hash)
        state_file = state_dir / "processed_hashes.json"
        state_file.write_text("{broken", encoding="utf-8")
        broken = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert broken.refresh()
        unrelated_hash = f"sha256:{'a' * 64}"
        atomic_json_write(state_file, {"version": 1, "hashes": [unrelated_hash]})
        merged = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert merged.refresh()
        persisted = json.loads(state_file.read_text(encoding="utf-8"))
        assert sorted(persisted["hashes"]) == sorted([content_hash, unrelated_hash])
