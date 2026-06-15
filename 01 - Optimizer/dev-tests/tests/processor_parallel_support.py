from __future__ import annotations

import threading

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import IngestionConfig, OutputFilters
from ingestion_layer_vision.processor import Processor
from processor_concurrency_env import VisionPluginManager, apply_processor_monkeypatches, make_processor_env


class TestParallelCancelDuringProcessing:
    def test_parallel_cancel_during_processing(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        proc, *_ = make_processor_env(tmp_path, num_files=10, parallel_workers=2)
        invoke_count = 0
        invoke_lock = threading.Lock()
        original_invoke = VisionPluginManager.invoke

        def cancelling_invoke(self, plugin_name, file_path, config_override=None):
            nonlocal invoke_count
            with invoke_lock:
                invoke_count += 1
                current = invoke_count
            if current >= 2:
                proc.cancel()
            return original_invoke(self, plugin_name, file_path, config_override)

        monkeypatch.setattr(VisionPluginManager, "invoke", cancelling_invoke)

        report = proc.process()
        assert report.total_files_processed < 10


class TestParallelWorkerException:
    def test_parallel_worker_exception_does_not_corrupt_report(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        proc, *_ = make_processor_env(tmp_path, num_files=5, parallel_workers=2)
        original_process_file = Processor._process_file

        def failing_process_file(self_proc, entry):
            if entry.filename == "file2.txt":
                raise RuntimeError("deliberate test explosion")
            return original_process_file(self_proc, entry)

        monkeypatch.setattr(Processor, "_process_file", failing_process_file)

        report = proc.process()

        assert report.successful + report.failed + 1 >= 5
        assert any("file2.txt" in str(err) for err in report.errors) or report.successful == 4


class TestConcurrentWriteExtractCollisionAvoidance:
    def test_concurrent_write_extract_collision_avoidance(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        proc, input_dir, output_dir, *_ = make_processor_env(tmp_path, num_files=1)
        extracts_dir = output_dir / "raw_extracts"
        extracts_dir.mkdir(parents=True, exist_ok=True)
        proc._extracts_dir = extracts_dir
        extract = proc.process_single(input_dir / "file0.txt", write_output=False)[0]
        results, errors = _run_two_extract_writers(proc, extract, extracts_dir)

        assert errors[0] is None, f"Thread 0 raised: {errors[0]}"
        assert errors[1] is None, f"Thread 1 raised: {errors[1]}"
        assert results[0] is not None
        assert results[1] is not None
        assert results[0] != results[1]


class TestConcurrentClaimOutputDir:
    def test_concurrent_claim_output_dir_only_one_wins(self, tmp_path):
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        claim_dir = tmp_path / "claim_target"
        for path in (input_dir, output_dir, state_dir, claim_dir):
            path.mkdir()
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        input_catalog.refresh()
        config = IngestionConfig()
        plugin_mgr = VisionPluginManager()
        proc1 = Processor(config, plugin_mgr, input_catalog, OutputFilters(), output_dir)
        proc2 = Processor(config, plugin_mgr, input_catalog, OutputFilters(), output_dir)
        results = _run_two_claims(proc1, proc2, claim_dir)

        wins = [item for item in results if item is not None]
        losses = [item for item in results if item is None]
        assert len(wins) == 1
        assert len(losses) == 1
        assert wins[0] == claim_dir


def _run_two_extract_writers(proc, extract, extracts_dir):
    barrier = threading.Barrier(2)
    results = [None, None]
    errors = [None, None]

    def write_thread(index):
        try:
            barrier.wait(timeout=5)
            results[index] = proc._write_extract(extract, extracts_dir)
        except Exception as exc:
            errors[index] = exc

    threads = [threading.Thread(target=write_thread, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results, errors


def _run_two_claims(proc1, proc2, claim_dir):
    barrier = threading.Barrier(2)
    results = [None, None]

    def claim_thread(index, proc_instance):
        barrier.wait(timeout=5)
        results[index] = proc_instance._try_claim_output_dir(claim_dir)

    threads = [
        threading.Thread(target=claim_thread, args=(0, proc1)),
        threading.Thread(target=claim_thread, args=(1, proc2)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results
