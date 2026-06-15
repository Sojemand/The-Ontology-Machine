from processor_test_shared import *


class ProcessSingleCoreCases:
    def test_process_single_returns_extracts(self, processing_env, tmp_path):
        env = processing_env
        # Testdatei
        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        proc = Processor(env["config"], env["plugin_mgr"])
        extracts = proc.process_single(test_file, write_output=False)
        assert len(extracts) == 1
        assert extracts[0].source.filename == "hello.txt"
        assert len(extracts[0].blocks) >= 1

    def test_non_vision_paths_unchanged_by_ocr_hardening(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "plain.txt"
        test_file.write_text("No vision path required", encoding="utf-8")

        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )
        extracts = proc.process_single(test_file, write_output=False)

        assert len(extracts) == 1
        extract = extracts[0]
        assert extract.needs_llm_vision is False
        assert extract.image_paths == []
        assert extract.extraction.plugin_name == "markdown-text"

    def test_process_single_writes_output(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "data.txt"
        test_file.write_text("Test data", encoding="utf-8")
        out_dir = tmp_path / "single_output"
        out_dir.mkdir()

        proc = Processor(env["config"], env["plugin_mgr"])
        extracts = proc.process_single(test_file, write_output=True, output_dir=out_dir)
        assert len(extracts) == 1

        raw_files = list((out_dir / "raw_extracts").glob("*.raw.json"))
        assert len(raw_files) == 1

        with open(raw_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["schema_version"] == "optimizer_raw_v2"
        assert "guardrail" not in data
        assert "block_refs" not in data
        assert data["source"]["ingest_id"]

    def test_process_single_writes_to_explicit_targets(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        raw_output_path = tmp_path / "managed" / "raw_extracts" / "scan.raw.json"
        page_assets_dir = tmp_path / "managed" / "page_assets" / "scan.abcd1234"

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)

        def render_to_explicit_dir(file_path, output_dir=None, *, page_assets_dir=None, asset_key=None, **kwargs):
            del file_path, output_dir, asset_key, kwargs
            target_dir = Path(str(page_assets_dir))
            target_dir.mkdir(parents=True, exist_ok=True)
            paths: list[str] = []
            for page in range(1, 3):
                page_path = target_dir / f"page_{page:03d}.png"
                page_path.write_bytes(b"image-bytes")
                paths.append(str(page_path))
            return paths

        monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", render_to_explicit_dir)

        proc = Processor(
            env["config"],
            _VisionPluginManager(),
        )
        extracts = proc.process_single(
            pdf_file,
            write_output=True,
            raw_output_path=raw_output_path,
            page_assets_dir=page_assets_dir,
            logical_source_path="queue/scan.pdf",
        )

        assert len(extracts) == 3
        assert raw_output_path.exists()
        assert (raw_output_path.parent / "scan.p001.of002.raw.json").exists()
        assert (raw_output_path.parent / "scan.p002.of002.raw.json").exists()
        assert sorted(path.name for path in page_assets_dir.glob("*.png")) == ["page_001.png", "page_002.png"]
        assert all(Path(path).parent == page_assets_dir for path in extracts[0].image_paths)

        with open(raw_output_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        assert data["source"]["file_path"] == "queue/scan.pdf"
        assert data["source"]["file_name"] == "scan.pdf"
        assert data["source"]["relative_path"] == "queue/scan.pdf"
        with open(raw_output_path.parent / "scan.p001.of002.raw.json", "r", encoding="utf-8") as handle:
            first_page = json.load(handle)
        with open(raw_output_path.parent / "scan.p002.of002.raw.json", "r", encoding="utf-8") as handle:
            second_page = json.load(handle)
        assert first_page["source"]["file_path"] == "queue/scan.pdf::page=001-of-002"
        assert second_page["source"]["file_path"] == "queue/scan.pdf::page=002-of-002"
        assert first_page["source"]["content_hash"] != data["source"]["content_hash"]
        assert second_page["source"]["content_hash"] != data["source"]["content_hash"]
        assert first_page["source"]["content_hash"] != second_page["source"]["content_hash"]
        assert first_page["context"]["page_number"] == 1
        assert second_page["context"]["page_number"] == 2
        assert first_page["context"]["document_page_count"] == 2
        assert second_page["context"]["document_page_count"] == 2
        assert first_page["context"]["source_document_path"] == "queue/scan.pdf"
        assert second_page["context"]["source_document_path"] == "queue/scan.pdf"

    def test_process_single_explicit_targets_require_complete_output_plan(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "data.txt"
        test_file.write_text("Test data", encoding="utf-8")

        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )

        with pytest.raises(ValueError, match="Explizite Zielpfade erfordern"):
            proc.process_single(
                test_file,
                write_output=True,
                raw_output_path=tmp_path / "managed" / "raw_extracts" / "data.raw.json",
                page_assets_dir=tmp_path / "managed" / "page_assets" / "data.abcd1234",
            )

    def test_process_single_write_output_requires_output_target(self, processing_env, tmp_path):
        env = processing_env
        test_file = tmp_path / "data.txt"
        test_file.write_text("Test data", encoding="utf-8")

        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )

        with pytest.raises(ValueError, match="write_output=True"):
            proc.process_single(test_file, write_output=True)
