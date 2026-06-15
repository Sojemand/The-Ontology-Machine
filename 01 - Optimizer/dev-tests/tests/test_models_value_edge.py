"""Config and value-boundary edge tests for ingestion_layer_vision.models."""
from __future__ import annotations

import pytest

from ingestion_layer_vision.models import FileFormat, IngestionConfig, PluginManifest, human_size


class TestConfigDefaults:
    def test_config_defaults_match_spec(self):
        cfg = IngestionConfig()
        assert cfg.max_file_size_mb == 100
        assert cfg.max_blocks_per_file == 50000
        assert cfg.max_cell_text_length == 8000
        assert cfg.processing_order == "input"
        assert cfg.plugin_timeout_seconds == 120
        assert cfg.parallel_workers == 1


class TestFileFormatFromExt:
    @pytest.mark.parametrize(
        "ext, expected",
        [
            (".pdf", FileFormat.PDF),
            (".jpg", FileFormat.IMAGE),
            (".png", FileFormat.IMAGE),
            (".txt", FileFormat.TEXT),
            (".yaml", FileFormat.TEXT),
            (".xlsx", FileFormat.UNKNOWN),
            (".docx", FileFormat.UNKNOWN),
            (".msg", FileFormat.UNKNOWN),
            (".xyz", FileFormat.UNKNOWN),
            (".PDF", FileFormat.PDF),
            (".Txt", FileFormat.TEXT),
        ],
    )
    def test_file_format_from_ext_common_formats(self, ext: str, expected: str):
        assert FileFormat.from_ext(ext) == expected


class TestHumanSizeBoundary:
    def test_human_size_boundary_values(self):
        assert human_size(0) == "0 B"
        assert human_size(1023) == "1023 B"
        assert human_size(1024) == "1.0 KB"
        assert "KB" in human_size(1048575)
        assert human_size(1048576) == "1.0 MB"


class TestPluginManifestDefaults:
    def test_plugin_manifest_missing_fields_defaults(self):
        manifest = PluginManifest(name="test-plugin", version="1.0.0")
        assert manifest.description == ""
        assert manifest.author == ""
        assert manifest.formats == []
        assert manifest.also_handles == []
        assert manifest.capabilities == []
        assert manifest.priority == 0
        assert manifest.system_dependencies == []
        assert manifest.config_schema == {}
        assert manifest.config == {}
