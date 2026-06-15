from __future__ import annotations

import json

import pytest

from ingestion_layer_vision.models import IngestionConfig, load_config


class TestConfig:
    def test_load_defaults_and_custom(self, tmp_path, tmp_config_dir):
        defaults = load_config(tmp_path / "nonexistent.yaml")
        assert defaults.max_file_size_mb == 100
        assert defaults.max_blocks_per_file == 50000
        custom = load_config(tmp_config_dir / "config.yaml")
        assert custom.max_file_size_mb == 100
        assert custom.processing_order == "input"

    def test_load_invalid_values_fail_closed(self, tmp_path):
        config_path = tmp_path / "bad.yaml"
        config_path.write_text(json.dumps({"parallel_workers": "four", "plugin_timeout_seconds": "slow", "processing_order": "sideways"}), encoding="utf-8")
        with pytest.raises(ValueError, match="processing_order|plugin_timeout_seconds|parallel_workers"):
            load_config(config_path)


class TestConfigFromDict:
    def test_from_dict_variants(self, caplog):
        basic = IngestionConfig.from_dict({"max_file_size_mb": 50, "processing_order": "size_desc"})
        assert basic.max_file_size_mb == 50
        assert basic.processing_order == "size_desc"
        ignored = IngestionConfig.from_dict({"max_file_size_mb": 50, "unknown_field": "ignored"})
        assert not hasattr(ignored, "unknown_field")
        assert IngestionConfig.from_dict({}).max_file_size_mb == 100
        invalid = IngestionConfig.from_dict({"parallel_workers": 0, "plugin_timeout_seconds": "never", "processing_order": "alpha"})
        assert invalid.parallel_workers == 1
        assert invalid.plugin_timeout_seconds == 120
        assert invalid.processing_order == "input"
        assert "Ungueltiger Config-Wert" in caplog.text
