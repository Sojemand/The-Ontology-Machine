from __future__ import annotations

import json
import threading
import uuid

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import atomic_json_write
from input_catalog_support import write_completed_raw


class TestConcurrentOperations:
    def test_concurrent_mark_processed_hash(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        catalog = InputCatalog(state_dir=state_dir)
        hashes = [f"sha256:{('%02x' % i) * 32}" for i in range(10)]
        barrier = threading.Barrier(len(hashes))
        errors: list[Exception] = []

        def mark_value(value: str) -> None:
            try:
                barrier.wait(timeout=5)
                catalog.mark_processed_hash(value)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=mark_value, args=(value,)) for value in hashes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert not errors
        persisted = json.loads((state_dir / "processed_hashes.json").read_text(encoding="utf-8"))
        assert len(persisted["hashes"]) == 10


class TestIterInput:
    def test_iter_input_excludes_output_and_state(self, tmp_path):
        input_dir = tmp_path / "input"
        state_dir = input_dir / "state"
        output_dir = input_dir / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "keep_a.txt").write_text("a", encoding="utf-8")
        (input_dir / "keep_b.txt").write_text("b", encoding="utf-8")
        (state_dir / "state_file.json").write_text("{}", encoding="utf-8")
        (output_dir / "output_file.json").write_text("{}", encoding="utf-8")
        catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        catalog.refresh()
        assert {entry.filename for entry in catalog.iter_entries()} == {"keep_a.txt", "keep_b.txt"}

    def test_iter_input_none_path_raises(self):
        try:
            list(InputCatalog()._iter_input_files())
        except ValueError:
            return
        raise AssertionError("ValueError expected")

    def test_collect_hashes_from_runs_dir(self, tmp_path):
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        write_completed_raw(output_dir, "test", "sha256:" + "a1" * 32, ingest_id=str(uuid.uuid4()))
        write_completed_raw(output_dir / "runs" / "run1", "test2", "sha256:" + "b2" * 32, ingest_id=str(uuid.uuid4()))
        found = InputCatalog(output_dir=output_dir, state_dir=state_dir)._collect_existing_output_hashes()
        assert "sha256:" + "a1" * 32 in found
        assert "sha256:" + "b2" * 32 in found
