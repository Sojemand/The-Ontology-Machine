from processor_test_shared import *


class TestBlockFormattingParsing:
    def test_legacy_merged_range_maps_to_merged_with(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"],
        )
        blocks = proc._parse_blocks([{
            "id": "S1_R1_CA",
            "type": "cell",
            "position": {"sheet": "Sheet1", "row": 1, "col": 1, "col_letter": "A"},
            "value": "Header",
            "value_type": "text",
            "formatting": {"merged_range": "A1:C1"},
            "confidence": None,
        }])
        assert blocks[0].formatting is not None
        assert blocks[0].formatting.merged_with == ["A1:C1"]


class TestProcessorCleanup:
    def test_cleanup_generated_output_ignores_paths_outside_page_assets(self, processing_env, tmp_path):
        env = processing_env
        proc = Processor(
            env["config"],
            env["plugin_mgr"],
        )

        outside_dir = tmp_path / "outside-assets"
        outside_dir.mkdir()
        outside_file = outside_dir / "page_001.png"
        outside_file.write_bytes(b"keep")

        proc._cleanup_generated_output(
            output_dir=env["output_dir"],
            raw_paths=[],
            image_paths=[str(outside_file)],
            asset_dirs=[],
            ingest_id="11111111-1111-1111-1111-111111111111",
        )

        assert outside_dir.exists()
        assert outside_file.exists()


# â”€â”€ Archivierung â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestNoArchiveOutput:
    def test_archive_is_not_created(self, processing_env):
        env = processing_env
        proc = Processor(
            env["config"], env["plugin_mgr"], env["input_catalog"],
            OutputFilters(), env["output_dir"],
        )
        proc.process()

        archive_dir = env["output_dir"] / "archive"
        assert not archive_dir.exists()


# â”€â”€ Clustering-Integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
