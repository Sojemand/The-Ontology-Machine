from processor_test_shared import *


class ProcessorBatchResilienceCases:
    def test_render_failure_cleans_precreated_assets_in_batch_mode(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()

        pdf_file = input_dir / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert input_catalog.refresh()

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)

        def fail_render(file_path, output_dir_arg, *, asset_key=None, **kwargs):
            del file_path, kwargs
            asset_dir = Path(output_dir_arg) / "page_assets" / str(asset_key)
            asset_dir.mkdir(parents=True, exist_ok=True)
            (asset_dir / "page_001.png").write_bytes(b"partial")
            raise OSError("renderer crashed")

        monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", fail_render)

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
            input_catalog,
            OutputFilters(),
            output_dir,
        )
        report = proc.process()

        assert report.successful == 0
        assert report.failed == 1
        assert list((output_dir / "raw_extracts").glob("*.raw.json")) == []
        assert list((output_dir / "page_assets").glob("*")) == []

    def test_sequential_process_survives_plugin_invoke_exception(self, processing_env):
        env = processing_env

        class FlakyPluginManager:
            def get_plugin_for_format(self, ext):
                return "text-plugin" if ext == ".txt" else None

            def invoke(self, plugin_name, file_path, config_override=None):
                del plugin_name, config_override
                if file_path.name == "test0.txt":
                    raise RuntimeError("plugin boom")
                return ExtractResult(
                    status="success",
                    blocks=_text_blocks(file_path.name),
                    metadata={},
                    errors=[],
                    processing_time_ms=1,
                )

            def get_manifest(self, _plugin_name):
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        proc = Processor(
            env["config"], FlakyPluginManager(), env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()

        assert report.total_files_processed == 3
        assert report.successful == 2
        assert report.failed == 1
        assert any("plugin boom" in item["error"] for item in report.errors)
        assert len(list((env["output_dir"] / "raw_extracts").glob("*.raw.json"))) == 2

    def test_sequential_process_survives_scan_detector_exception(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        state_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "scan-a.pdf").write_bytes(b"%PDF-1.4 a")
        (input_dir / "scan-b.pdf").write_bytes(b"%PDF-1.4 b")

        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert input_catalog.refresh()

        class PdfPluginManager:
            def get_plugin_for_format(self, ext):
                return "pdf-plugin" if ext == ".pdf" else None

            def invoke(self, _plugin_name, file_path, config_override=None):
                del file_path, config_override
                return ExtractResult(
                    status="success",
                    blocks=_text_blocks("pdf"),
                    metadata={},
                    errors=[],
                    processing_time_ms=1,
                )

            def get_manifest(self, _plugin_name):
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        scan_calls = {"count": 0}

        def flaky_is_scan(*_args, **_kwargs):
            scan_calls["count"] += 1
            if scan_calls["count"] == 1:
                raise RuntimeError("scan detector boom")
            return False

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", flaky_is_scan)

        proc = Processor(
            env["config"], PdfPluginManager(), input_catalog,
            OutputFilters(), output_dir,
        )
        report = proc.process()

        assert report.total_files_processed == 2
        assert report.successful == 1
        assert report.failed == 1
        assert any("Scan-Erkennung fehlgeschlagen" in item["error"] for item in report.errors)
        assert len(list((output_dir / "raw_extracts").glob("*.raw.json"))) == 1

    def test_sequential_process_survives_extract_build_exception(self, processing_env, monkeypatch):
        env = processing_env
        original = Processor._build_extract
        calls = {"count": 0}

        def flaky_build(self, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("build exploded")
            return original(self, **kwargs)

        monkeypatch.setattr(Processor, "_build_extract", flaky_build)

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()

        assert report.total_files_processed == 3
        assert report.successful == 2
        assert report.failed == 1
        assert any("build exploded" in item["error"] for item in report.errors)
        assert len(list((env["output_dir"] / "raw_extracts").glob("*.raw.json"))) == 2
