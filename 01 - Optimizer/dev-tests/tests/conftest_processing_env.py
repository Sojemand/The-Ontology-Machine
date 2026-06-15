"""Processor-specific fixtures for Optimizer dev-tests."""
from __future__ import annotations

import pytest

from conftest_project_env import build_project_root
from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import IngestionConfig
from ingestion_layer_vision.plugin_manager import PluginManager


@pytest.fixture
def processing_env(tmp_path):
    root, input_dir, output_dir, state_dir, config_dir, plugins_dir = build_project_root(tmp_path)
    config = IngestionConfig(plugin_timeout_seconds=10)
    plugin_mgr = PluginManager(plugins_dir, config)
    for index in range(3):
        (input_dir / f"test{index}.txt").write_text(f"Content {index}", encoding="utf-8")
    input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
    input_catalog.refresh()
    return {
        "root": root,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "state_dir": state_dir,
        "config_dir": config_dir,
        "plugins_dir": plugins_dir,
        "config": config,
        "plugin_mgr": plugin_mgr,
        "input_catalog": input_catalog,
    }

