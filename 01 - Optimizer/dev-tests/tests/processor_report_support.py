from __future__ import annotations

import threading

from ingestion_layer_vision.input_catalog import CatalogEntry
from ingestion_layer_vision.models import ExtractResult
from ingestion_layer_vision.processor import Processor
from processor_concurrency_env import apply_processor_monkeypatches, make_empty_processor, make_processor_env


class TestReportCounterConsistency:
    def test_report_counter_consistency_under_parallel_workers(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        proc, *_ = make_processor_env(tmp_path, num_files=20, parallel_workers=4)
        report = proc.process()

        assert report.total_files_processed == report.successful + report.failed


class TestRollbackExtractReport:
    def test_rollback_extract_report_undoes_exact_counters(self, tmp_path):
        proc = make_empty_processor(tmp_path)
        _seed_report(proc)

        proc._rollback_extract_report(
            written_extract_count=1,
            block_count=10,
            image_count=2,
            fmt="pdf",
            plugin_name="test",
            vision=True,
        )

        assert proc._report.total_extracts_written == 2
        assert proc._report.total_blocks_generated == 20
        assert proc._report.total_images_rendered == 4
        assert proc._report.by_format["pdf"] == 2
        assert proc._report.by_plugin["test"] == 2
        assert proc._report.vision_docs == 1
        assert proc._report.text_docs == 1

    def test_rollback_with_zero_written_extracts_is_noop(self, tmp_path):
        proc = make_empty_processor(tmp_path)
        _seed_report(proc)

        proc._rollback_extract_report(
            written_extract_count=0,
            block_count=10,
            image_count=2,
            fmt="pdf",
            plugin_name="test",
            vision=True,
        )

        assert proc._report.total_extracts_written == 3
        assert proc._report.total_blocks_generated == 30
        assert proc._report.total_images_rendered == 6
        assert proc._report.by_format["pdf"] == 3
        assert proc._report.by_plugin["test"] == 3
        assert proc._report.vision_docs == 2
        assert proc._report.text_docs == 1

    def test_rollback_never_makes_counters_negative(self, tmp_path):
        proc = make_empty_processor(tmp_path)
        _seed_report(proc, count=1, blocks=1, images=1, vision_docs=1)

        proc._rollback_extract_report(
            written_extract_count=5,
            block_count=100,
            image_count=50,
            fmt="pdf",
            plugin_name="test",
            vision=True,
        )

        assert proc._report.total_extracts_written == 0
        assert proc._report.total_blocks_generated == 0
        assert proc._report.total_images_rendered == 0
        assert "pdf" not in proc._report.by_format
        assert "test" not in proc._report.by_plugin
        assert proc._report.vision_docs == 0
        assert proc._report.text_docs == 1


class TestReportLockProtectsConcurrentUpdates:
    def test_report_lock_protects_concurrent_by_format_updates(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        proc, input_dir, output_dir, *_ = make_processor_env(tmp_path, num_files=1)
        extracts_dir = output_dir / "raw_extracts"
        extracts_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Processor, "_write_extract", _fake_extract_writer(extracts_dir))
        test_file = input_dir / "file0.txt"
        content_hash = Processor._compute_hash(test_file)
        entry = CatalogEntry(
            path=test_file,
            filename="file0.txt",
            extension=".txt",
            size_bytes=test_file.stat().st_size,
            created="",
            modified="",
            relative_path="file0.txt",
            content_hash=content_hash,
        )
        result = ExtractResult(status="success", blocks=[], metadata={}, errors=[], processing_time_ms=1)
        errors = _run_concurrent_builds(proc, entry, test_file, result, content_hash)

        assert not errors, f"Threads raised errors: {errors}"
        assert proc._report.total_extracts_written == 10
        assert proc._report.by_format.get("text", 0) == 10
        assert proc._report.by_plugin.get("text-plugin", 0) == 10
        assert proc._report.text_docs == 10


def _seed_report(proc, *, count=3, blocks=30, images=6, vision_docs=2) -> None:
    proc._report.total_extracts_written = count
    proc._report.total_blocks_generated = blocks
    proc._report.total_images_rendered = images
    proc._report.by_format = {"pdf": count}
    proc._report.by_plugin = {"test": count}
    proc._report.vision_docs = vision_docs
    proc._report.text_docs = 1


def _fake_extract_writer(extracts_dir):
    dummy_counter = {"n": 0}
    dummy_lock = threading.Lock()

    def fake_write_extract(self_proc, extract, ed):
        del self_proc, extract
        with dummy_lock:
            dummy_counter["n"] += 1
            n = dummy_counter["n"]
        dummy_path = ed / f"dummy_{n}.raw.json"
        dummy_path.write_text("{}", encoding="utf-8")
        return dummy_path

    return fake_write_extract


def _run_concurrent_builds(proc, entry, test_file, result, content_hash) -> list[BaseException]:
    barrier = threading.Barrier(10)
    errors = []

    def worker():
        try:
            barrier.wait(timeout=5)
            proc._build_and_write_extract(
                entry=entry,
                file_path=test_file,
                filename="file0.txt",
                ext=".txt",
                fmt="text",
                relative_path="file0.txt",
                size=test_file.stat().st_size,
                result=result,
                plugin_name="text-plugin",
                blocks=[],
                vision=False,
                scan_detected=False,
                ocr_was_used=False,
                image_paths=[],
                content_hash=content_hash,
                ingest_id="test-id",
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    return errors
