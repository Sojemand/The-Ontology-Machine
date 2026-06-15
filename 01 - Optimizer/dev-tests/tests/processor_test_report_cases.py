from processor_test_shared import *


class TestProcessorCancel:
    def test_cancel_stops_processing(self, processing_env):
        env = processing_env
        reports = []

        def on_update(r):
            reports.append(r)

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
            callback=on_update,
        )
        # Cancel sofort
        proc.cancel()
        report = proc.process()
        assert report.total_files_processed == 0


class TestProcessorReport:
    def test_report_written(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        proc.process()

        report_path = env["output_dir"] / "ingestion_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["successful"] == 3
        assert data["total_files_processed"] == 3

        # v2.0 Report-Felder
        assert "vision_docs" in data
        assert "text_docs" in data
        assert "total_images_rendered" in data
        assert "total_extracts_written" in data
        assert data["vision_docs"] + data["text_docs"] == data["total_extracts_written"]

    def test_callback_called(self, processing_env):
        env = processing_env
        reports = []

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
            callback=lambda r: reports.append(r),
        )
        proc.process()
        # Mindestens der finale Callback
        assert len(reports) >= 1

    def test_callback_exceptions_do_not_abort_or_skip_shutdown(self, processing_env, monkeypatch):
        env = processing_env
        shutdown_calls = []

        def fail_callback(_report):
            raise RuntimeError("callback boom")

        monkeypatch.setattr(env["plugin_mgr"], "shutdown_workers", lambda: shutdown_calls.append(True))

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
            callback=fail_callback,
        )
        report = proc.process()

        assert report.successful == 3
        assert shutdown_calls == [True]

    def test_parallel_callback_exceptions_do_not_abort_or_skip_shutdown(self, processing_env, monkeypatch):
        env = processing_env
        shutdown_calls = []

        def fail_callback(_report):
            raise RuntimeError("callback boom")

        env["config"].parallel_workers = 2
        monkeypatch.setattr(env["plugin_mgr"], "shutdown_workers", lambda: shutdown_calls.append(True))

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
            callback=fail_callback,
        )
        report = proc.process()

        assert report.successful == 3
        assert shutdown_calls == [True]

    def test_report_write_failure_raises(self, processing_env, monkeypatch):
        env = processing_env
        shutdown_calls = []

        def failing_atomic_write(path, data):
            if path.name == "ingestion_report.json":
                raise OSError("report locked")
            return model_atomic_json_write(path, data)

        monkeypatch.setattr("ingestion_layer_vision.processor.atomic_json_write", failing_atomic_write)
        monkeypatch.setattr(env["plugin_mgr"], "shutdown_workers", lambda: shutdown_calls.append(True))

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(batch_size=1), env["output_dir"],
        )

        with pytest.raises(OSError, match="report locked"):
            proc.process()
        assert shutdown_calls == [True]


# â”€â”€ process_single() â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
