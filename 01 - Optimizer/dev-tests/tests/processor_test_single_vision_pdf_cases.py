from processor_test_shared import *


class ProcessSingleVisionPdfCases:
    def test_vision_pdf_writes_single_extract_for_multi_page_scan(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        pdf_file = tmp_path / "scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        out_dir = tmp_path / "vision_output"
        out_dir.mkdir()

        raw_blocks = [
            {
                "id": "P1_H1",
                "type": "paragraph",
                "position": {"page": 1, "paragraph_index": 0},
                "value": "Muster GmbH",
                "value_type": "text",
                "formatting": None,
                "confidence": 0.99,
            },
            {
                "id": "P1_F1",
                "type": "paragraph",
                "position": {"page": 1, "paragraph_index": 1},
                "value": "Rechnungsnummer: RE-2026-001",
                "value_type": "text",
                "formatting": None,
                "confidence": 0.98,
            },
            {
                "id": "P2_T1",
                "type": "paragraph",
                "position": {"page": 2, "paragraph_index": 0},
                "value": "Gesamt: 1200,00 EUR",
                "value_type": "text",
                "formatting": None,
                "confidence": 0.97,
            },
        ]

        class StubVisionPluginManager:
            def get_plugin_for_format(self, ext):
                return "pdf-plugin" if ext == ".pdf" else None

            def invoke(self, plugin_name, file_path, config_override=None):
                del plugin_name, file_path, config_override
                return ExtractResult(
                    status="success",
                    blocks=raw_blocks,
                    metadata={
                        "ocr_quality_mode": "best_quality",
                        "ocr_render_dpi_used": 450,
                        "ocr_variant_count": 5,
                        "ocr_second_pass_regions": 2,
                        "ocr_lines_merged": 6,
                        "ocr_deskew_applied": True,
                        "ocr_avg_confidence": 0.96,
                        "ocr_min_confidence": 0.72,
                    },
                    errors=[],
                    processing_time_ms=1,
                )

            def get_manifest(self, plugin_name):
                del plugin_name
                return SimpleNamespace(version="1.0.0", capabilities=["text"])

            def shutdown_workers(self):
                return None

            def kill_all(self):
                return None

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)
        monkeypatch.setattr(
            "ingestion_layer_vision.processor.render_page_assets",
            _render_stub_pages,
        )

        proc = Processor(
            env["config"],
            StubVisionPluginManager(),
        )
        extracts = proc.process_single(pdf_file, write_output=True, output_dir=out_dir)

        assert len(extracts) == 1
        extract = extracts[0]
        assert extract.needs_llm_vision is True
        assert len(extract.image_paths) == 2
        assert extract.page_number is None
        assert extract.total_pages is None
        assert extract.metadata["ocr_quality_mode"] == "best_quality"
        assert extract.metadata["page_count"] == 2

        raw_files = list((out_dir / "raw_extracts").glob("*.raw.json"))
        assert len(raw_files) == 1
        with open(raw_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["schema_version"] == "optimizer_raw_v2"
        assert data["source"]["page_count"] == 2
        assert data["metadata"]["ocr_quality_mode"] == "best_quality"
        assert len(data["ocr_reference"]["blocks"]) == 3
        assert "vision_assets" not in data

    def test_parallel_vision_same_basenames_keep_isolated_page_assets(self, processing_env, tmp_path, monkeypatch):
        env = processing_env
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        (input_dir / "a").mkdir(parents=True)
        (input_dir / "b").mkdir(parents=True)
        state_dir.mkdir()
        output_dir.mkdir()
        (input_dir / "a" / "same.pdf").write_bytes(b"%PDF-1.4 alpha")
        (input_dir / "b" / "same.pdf").write_bytes(b"%PDF-1.4 beta")

        config = IngestionConfig(parallel_workers=2, plugin_timeout_seconds=10)
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert input_catalog.refresh()

        monkeypatch.setattr("ingestion_layer_vision.processor.is_scan", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.should_use_vision", lambda *_args, **_kwargs: True)
        monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", _render_stub_pages)

        proc = Processor(
            config,
            _VisionPluginManager(),
            input_catalog,
            OutputFilters(),
            output_dir,
        )
        report = proc.process()

        assert report.successful == 2
        page_dirs = sorted(path.name for path in (output_dir / "page_assets").iterdir())
        assert len(page_dirs) == 2
        assert page_dirs[0] != page_dirs[1]

        raw_parent_names = set()
        for raw_file in (output_dir / "raw_extracts").glob("*.raw.json"):
            with open(raw_file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            assert payload["schema_version"] == "optimizer_raw_v2"
            assert "vision_assets" not in payload
        assert len(raw_parent_names) == 0
