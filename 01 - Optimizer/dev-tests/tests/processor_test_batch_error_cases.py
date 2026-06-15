from processor_test_shared import *


class ProcessorBatchErrorCases:
    def test_file_not_found(self, processing_env, tmp_path):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()

        missing_file = input_dir / "file.txt"
        missing_file.write_text("temp", encoding="utf-8")
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        input_catalog.refresh()
        missing_file.unlink()

        proc = Processor(
            env["config"], env["plugin_mgr"], input_catalog,
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()
        assert report.failed == 1
        assert len(report.errors) == 1

    def test_no_plugin_for_format(self, processing_env, tmp_path):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()

        data_file = tmp_path / "file.xyz"
        data_file.write_text("data", encoding="utf-8")
        target_file = input_dir / "file.xyz"
        target_file.write_text("data", encoding="utf-8")
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        input_catalog.refresh()

        proc = Processor(
            env["config"], env["plugin_mgr"], input_catalog,
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()
        assert report.failed == 1

    def test_raw_extract_write_failure_is_recorded(self, processing_env, monkeypatch):
        env = processing_env

        def failing_atomic_write(path, data):
            if path.name.endswith(".raw.json"):
                raise OSError("disk full")
            return model_atomic_json_write(path, data)

        monkeypatch.setattr("ingestion_layer_vision.processor.atomic_json_write", failing_atomic_write)

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(batch_size=1), env["output_dir"],
        )
        report = proc.process()

        assert report.successful == 0
        assert report.failed == 1
        assert report.total_extracts_written == 0
        assert any("Output schreiben fehlgeschlagen" in error["error"] for error in report.errors)

    def test_batch_required_llm_ocr_without_assets_is_recorded_as_failure(self, processing_env, tmp_path):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "needs-ocr.txt").write_text("ocr please", encoding="utf-8")
        (input_dir / "plain.txt").write_text("plain", encoding="utf-8")

        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert input_catalog.refresh()

        class NeedsOcrPluginManager:
            def get_plugin_for_format(self, ext):
                return "text-plugin" if ext == ".txt" else None

            def invoke(self, _plugin_name, file_path, config_override=None):
                del config_override
                return ExtractResult(
                    status="success",
                    blocks=_text_blocks(file_path.name),
                    metadata={},
                    errors=[],
                    processing_time_ms=1,
                    needs_ocr=file_path.name == "needs-ocr.txt",
                )

            def get_manifest(self, _plugin_name):
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        proc = Processor(
            env["config"], NeedsOcrPluginManager(), input_catalog,
            OutputFilters(), output_dir,
        )
        report = proc.process()

        assert report.total_files_processed == 2
        assert report.successful == 1
        assert report.failed == 1
        assert any("Vision-Assets fehlen" in item["error"] for item in report.errors)
        assert len(list((output_dir / "raw_extracts").glob("*.raw.json"))) == 1
