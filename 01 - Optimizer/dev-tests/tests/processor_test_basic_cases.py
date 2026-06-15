from processor_test_shared import *


class TestProcessorBasic:
    def test_process_empty_input_catalog(self, tmp_path):
        config = IngestionConfig()
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        plugin_mgr = PluginManager(plugins_dir, config)

        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        input_dir.mkdir()
        state_dir.mkdir()
        input_catalog = InputCatalog(input_dir, state_dir=state_dir)
        input_catalog.refresh()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        proc = Processor(config, plugin_mgr, input_catalog, OutputFilters(),
                          output_dir)
        report = proc.process()
        assert report.total_files_processed == 0
        assert report.successful == 0

    def test_parse_blocks_keeps_all_raw_blocks_without_config_limit(self):
        proc = Processor(IngestionConfig(max_blocks_per_file=1), SimpleNamespace())
        raw_blocks = [
            {"id": f"B{index}", "type": "paragraph", "position": {}, "value": f"value-{index}"}
            for index in range(3)
        ]

        blocks = proc._parse_blocks(raw_blocks)

        assert [block.value for block in blocks] == ["value-0", "value-1", "value-2"]

    def test_process_files(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()
        assert report.total_files_processed == 3
        assert report.successful == 3
        assert report.failed == 0

        # RawExtracts pruefen
        extracts = list((env["output_dir"] / "raw_extracts").glob("*.raw.json"))
        assert len(extracts) == 3

    def test_parallel_duplicate_basenames_keep_distinct_outputs(self, tmp_path):
        input_dir = tmp_path / "input"
        state_dir = tmp_path / "state"
        output_dir = tmp_path / "output"
        plugins_dir = tmp_path / "plugins"
        (input_dir / "a").mkdir(parents=True)
        (input_dir / "b").mkdir(parents=True)
        state_dir.mkdir()
        output_dir.mkdir()
        plugins_dir.mkdir()

        (input_dir / "a" / "same.txt").write_text("alpha", encoding="utf-8")
        (input_dir / "b" / "same.txt").write_text("beta", encoding="utf-8")

        config = IngestionConfig(parallel_workers=2, plugin_timeout_seconds=10)
        plugin_mgr = PluginManager(plugins_dir, config)
        input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
        assert input_catalog.refresh()

        proc = Processor(
            config,
            plugin_mgr,
            input_catalog,
            OutputFilters(),
            output_dir,
        )
        report = proc.process()

        raw_names = sorted(path.name for path in (output_dir / "raw_extracts").glob("*.raw.json"))
        assert report.total_files_processed == 2
        assert report.successful == 2
        assert report.total_extracts_written == 2
        assert raw_names == ["a__same.txt.raw.json", "b__same.txt.raw.json"]

    def test_process_uses_child_run_directory_when_output_is_active(self, processing_env):
        env = processing_env
        _mark_output_active(env["output_dir"])

        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()

        effective_output = Path(report.output_directory)
        assert effective_output.parent == env["output_dir"] / "runs"
        assert effective_output.exists()
        assert len(list((effective_output / "raw_extracts").glob("*.raw.json"))) == 3
        assert (effective_output / "ingestion_report.json").exists()
        assert not (env["output_dir"] / "raw_extracts").exists()

    def test_output_structure(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        proc.process()

        extract_path = env["output_dir"] / "raw_extracts" / "test0.txt.raw.json"
        assert extract_path.exists()
        with open(extract_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert set(data.keys()) >= {
            "schema_version",
            "optimizer_profile",
            "source",
            "extraction",
            "context",
            "ocr_reference",
        }
        assert data["schema_version"] == "optimizer_raw_v2"
        assert data["source"]["file_name"] == "test0.txt"
        assert data["source"]["document_type"] == "text"
        assert data["ocr_reference"]["blocks"]
        assert "guardrail" not in data
        assert "block_refs" not in data
        assert "vision_assets" not in data

    def test_successful_run_marks_hashes_as_processed(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        report = proc.process()
        assert report.successful == 3

        refreshed_catalog = InputCatalog(
            env["input_dir"],
            state_dir=env["state_dir"],
            output_dir=env["output_dir"],
        )
        assert refreshed_catalog.refresh()
        assert refreshed_catalog.total_count == 0
        assert refreshed_catalog.skipped_processed_count == 3


class TestProcessorFilter:
    def test_batch_size(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(batch_size=1), env["output_dir"],
        )
        report = proc.process()
        assert report.total_files_processed == 1
