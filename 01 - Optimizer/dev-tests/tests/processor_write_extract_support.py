from __future__ import annotations

from pathlib import Path
import threading

import pytest

from ingestion_layer_vision.models import IngestionConfig, atomic_json_write
from ingestion_layer_vision.processor import Processor, _OUTPUT_CLAIM_SUFFIX

from processor_write_edge_env import StubPluginManager, make_processor, minimal_extract


class TestWriteExtract:
    def test_write_extract_crash_after_create_cleans_empty_file(self, tmp_path, monkeypatch):
        proc = make_processor(tmp_path)

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated write failure")

        monkeypatch.setattr("ingestion_layer_vision.processor.atomic_json_write", _boom)

        with pytest.raises(RuntimeError, match="simulated write failure"):
            proc._write_extract(minimal_extract(), proc._extracts_dir)

        assert list(proc._extracts_dir.glob("*.raw.json")) == []
        assert list(proc._extracts_dir.glob("*.claim")) == []

    def test_write_extract_success_removes_claim_file(self, tmp_path):
        proc = make_processor(tmp_path)

        output_path = proc._write_extract(minimal_extract(), proc._extracts_dir)

        assert output_path.exists()
        assert list(proc._extracts_dir.glob("*.claim")) == []

    def test_write_extract_never_exposes_final_file_before_atomic_publish(self, tmp_path, monkeypatch):
        proc = make_processor(tmp_path)
        extract = minimal_extract()
        started = threading.Event()
        release = threading.Event()
        original_atomic_write = atomic_json_write
        observed: dict[str, object] = {}
        errors: list[Exception] = []

        def slow_atomic_write(path, data):
            started.set()
            observed["final_exists_before_publish"] = path.exists()
            observed["claim_exists_before_publish"] = Processor._output_claim_path(path).exists()
            release.wait(timeout=5)
            return original_atomic_write(path, data)

        monkeypatch.setattr("ingestion_layer_vision.processor.atomic_json_write", slow_atomic_write)

        def writer():
            try:
                observed["result_path"] = proc._write_extract(extract, proc._extracts_dir)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        thread = threading.Thread(target=writer)
        thread.start()
        assert started.wait(timeout=5), "atomic_json_write was never reached"
        assert list(proc._extracts_dir.glob("*.raw.json")) == []
        assert len(list(proc._extracts_dir.glob("*.claim"))) == 1

        release.set()
        thread.join(timeout=10)

        assert errors == []
        assert observed["final_exists_before_publish"] is False
        assert observed["claim_exists_before_publish"] is True
        assert Path(observed["result_path"]).exists()
        assert list(proc._extracts_dir.glob("*.claim")) == []

    def test_write_extract_all_64_retries_exhausted(self, tmp_path):
        proc = make_processor(tmp_path)
        extract = minimal_extract()
        content_hash = extract.source.content_hash
        relative_path = extract.source.relative_path
        short_hash = Processor._short_output_token(content_hash, relative_path)
        slug = Processor._build_output_slug(relative_path, content_hash)

        for candidate in Processor._iter_output_candidates(proc._extracts_dir, slug, "", short_hash):
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text("{}")

        with pytest.raises(FileExistsError):
            proc._write_extract(extract, proc._extracts_dir)

    def test_write_extract_page_suffix_formatting(self, tmp_path):
        proc = make_processor(tmp_path)
        extract = minimal_extract()
        extract.page_number = 5

        output_path = proc._write_extract(extract, proc._extracts_dir)
        assert "_p05" in output_path.name

    def test_write_extract_collision_uses_next_candidate(self, tmp_path):
        proc = make_processor(tmp_path)
        extract = minimal_extract()
        content_hash = extract.source.content_hash
        relative_path = extract.source.relative_path
        short_hash = Processor._short_output_token(content_hash, relative_path)
        slug = Processor._build_output_slug(relative_path, content_hash)
        candidates = list(Processor._iter_output_candidates(proc._extracts_dir, slug, "", short_hash))
        candidates[0].write_text("{}")

        assert proc._write_extract(extract, proc._extracts_dir) == candidates[1]

    def test_write_extract_budgets_long_names_for_deep_output_dir(self, tmp_path):
        deep_output = tmp_path
        for index in range(6):
            deep_output = deep_output / f"deep_segment_{index:02d}"
        deep_output.mkdir(parents=True, exist_ok=True)

        proc = Processor(IngestionConfig(), StubPluginManager(), output_dir=deep_output)
        proc._extracts_dir = deep_output / "raw_extracts"
        proc._extracts_dir.mkdir(parents=True, exist_ok=True)

        long_name = ("201611136 V - Reinhard Feinmechanik Dietzenbach - Bestellung Tieflochbohrungen " * 2).strip() + ".pdf"
        extract = minimal_extract(filename=long_name)
        extract.source.relative_path = long_name

        output_path = proc._write_extract(extract, proc._extracts_dir)

        assert output_path.exists()
        assert len(str(output_path)) <= 259 - len(_OUTPUT_CLAIM_SUFFIX)
        assert not list(proc._extracts_dir.glob("*.claim"))
