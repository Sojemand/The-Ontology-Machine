from processor_test_shared import *


class ProcessSingleVisionOutputCases:
    def test_process_single_vision_dry_run_requires_output_with_explicit_output_dir(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)
        monkeypatch.setattr(
            "ingestion_layer_vision.processor.render_page_assets",
            lambda *_args, **_kwargs: pytest.fail("render_page_assets must not run during dry-run"),
        )

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
        )
        with pytest.raises(ValueError, match="Vision-Dokumente erfordern"):
            proc.process_single(pdf_file, write_output=False, output_dir=out_dir)

        assert not (out_dir / "page_assets").exists()
        assert not (out_dir / "raw_extracts").exists()

    def test_process_single_vision_dry_run_requires_output_with_requested_output_dir(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)
        monkeypatch.setattr(
            "ingestion_layer_vision.processor.render_page_assets",
            lambda *_args, **_kwargs: pytest.fail("render_page_assets must not run during dry-run"),
        )

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
            output_dir=out_dir,
        )
        with pytest.raises(ValueError, match="Vision-Dokumente erfordern"):
            proc.process_single(pdf_file, write_output=False)

        assert not (out_dir / "page_assets").exists()
        assert not (out_dir / "raw_extracts").exists()

    def test_process_single_vision_same_basenames_get_isolated_page_assets(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()
        first = tmp_path / "a" / "same.pdf"
        second = tmp_path / "b" / "same.pdf"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_bytes(b"%PDF-1.4 alpha")
        second.write_bytes(b"%PDF-1.4 beta")

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", _render_stub_pages)

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
        )
        first_extract = proc.process_single(first, write_output=True, output_dir=out_dir)[0]
        second_extract = proc.process_single(second, write_output=True, output_dir=out_dir)[0]

        image_dirs = {
            Path(first_extract.image_paths[0]).parent.name,
            Path(second_extract.image_paths[0]).parent.name,
        }
        assert len(image_dirs) == 2
        assert len(list((out_dir / "page_assets").iterdir())) == 2

        raw_files = sorted((out_dir / "raw_extracts").glob("*.raw.json"))
        assert len(raw_files) == 2
        for raw_file in raw_files:
            with open(raw_file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            assert payload["schema_version"] == "optimizer_raw_v2"
            assert "vision_assets" not in payload
        assert image_dirs == {
            Path(first_extract.image_paths[0]).parent.name,
            Path(second_extract.image_paths[0]).parent.name,
        }

    def test_process_single_render_failure_cleans_precreated_asset_dir(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()

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
        )

        with pytest.raises(OSError, match="renderer crashed"):
            proc.process_single(pdf_file, write_output=True, output_dir=out_dir)

        assert list((out_dir / "raw_extracts").glob("*.raw.json")) == []
        assert list((out_dir / "page_assets").glob("*")) == []

    def test_process_single_empty_render_result_is_error_and_cleans_output(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)

        def partial_render(file_path, output_dir_arg, *, asset_key=None, **kwargs):
            del file_path, kwargs
            asset_dir = Path(output_dir_arg) / "page_assets" / str(asset_key)
            asset_dir.mkdir(parents=True, exist_ok=True)
            (asset_dir / "page_001.png").write_bytes(b"partial")
            return []

        monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", partial_render)

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
        )

        with pytest.raises(OSError, match="Vision-Assets fehlen"):
            proc.process_single(pdf_file, write_output=True, output_dir=out_dir)

        assert list((out_dir / "raw_extracts").glob("*.raw.json")) == []
        assert list((out_dir / "page_assets").glob("*")) == []
