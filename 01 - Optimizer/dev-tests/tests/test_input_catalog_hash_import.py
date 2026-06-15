from __future__ import annotations

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import atomic_json_write


class TestInputCatalogHashImport:
    def test_export_and_replace_import(self, tmp_path):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        state_dir.mkdir()
        (input_dir / "done.txt").write_text("already done", encoding="utf-8")
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert catalog.refresh()
        processed_hash = catalog.iter_entries()[0].content_hash
        catalog.mark_processed_hash(processed_hash)
        export_path = tmp_path / "saved_hashes.json"
        assert catalog.export_processed_hashes(export_path) == 1
        replacement = InputCatalog(input_dir, state_dir=state_dir)
        assert replacement.clear_processed_hashes() == 1
        assert replacement.import_processed_hashes(export_path, replace=True) == 1
        assert replacement.processed_hash_count == 1

    def test_import_replaces_existing_hashes(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        first_payload = tmp_path / "first.json"
        second_payload = tmp_path / "second.json"
        atomic_json_write(first_payload, {"version": 1, "hashes": [f"sha256:{'1' * 64}"]})
        atomic_json_write(second_payload, {"version": 1, "hashes": [f"sha256:{'2' * 64}"]})
        catalog = InputCatalog(state_dir=state_dir)
        assert catalog.import_processed_hashes(first_payload, replace=True) == 1
        assert catalog.import_processed_hashes(second_payload, replace=True) == 1
        assert catalog.processed_hash_count == 1

    def test_import_hash_normalization_and_invalid_entries(self, tmp_path, caplog):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        state_dir.mkdir()
        doc = input_dir / "done.txt"
        doc.write_text("already done", encoding="utf-8")
        seed = InputCatalog(input_dir, state_dir=state_dir)
        assert seed.refresh()
        bare_hash = seed.iter_entries()[0].content_hash.replace("sha256:", "")
        payload = tmp_path / "mixed_hashes.json"
        atomic_json_write(payload, {"version": 1, "hashes": [bare_hash, "not-a-hash", f"{'b' * 64}"]})
        catalog = InputCatalog(input_dir, state_dir=state_dir)
        assert catalog.import_processed_hashes(payload, replace=True) == 2
        refreshed = InputCatalog(input_dir, state_dir=state_dir)
        assert refreshed.refresh()
        assert refreshed.total_count == 0
        assert refreshed.skipped_processed_count == 1
        assert "ungueltige Hash-Eintraege" in caplog.text
