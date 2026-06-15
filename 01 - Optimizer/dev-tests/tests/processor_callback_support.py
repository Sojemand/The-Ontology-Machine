from __future__ import annotations

from processor_concurrency_env import apply_processor_monkeypatches, make_processor_env


class TestCallbackExceptionHandling:
    def test_callback_exception_does_not_stop_processing(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)

        def bad_callback(_report):
            raise ValueError("callback exploded")

        proc, *_ = make_processor_env(tmp_path, num_files=3, callback=bad_callback)
        report = proc.process()
        assert report.total_files_processed == 3


class TestProcessSequentialCallbackFires:
    def test_process_sequential_callback_fires(self, tmp_path, monkeypatch):
        apply_processor_monkeypatches(monkeypatch)
        callback_invocations = []

        def tracking_callback(report):
            callback_invocations.append(report)

        proc, *_ = make_processor_env(tmp_path, num_files=3, callback=tracking_callback)
        proc.process()
        assert len(callback_invocations) >= 1
