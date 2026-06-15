from __future__ import annotations

import json

from ingestion_layer_vision.models import IngestionConfig
from ingestion_layer_vision.plugin_manager import PluginManager


def test_invalid_custom_manifest_is_skipped(tmp_path, caplog):
    plugins_dir = tmp_path / "plugins"
    custom_plugin = plugins_dir / "markdown-text"
    custom_plugin.mkdir(parents=True)
    (custom_plugin / "extractor.py").write_text("# stub", encoding="utf-8")
    (custom_plugin / "plugin.json").write_text("{broken", encoding="utf-8")
    mgr = PluginManager(plugins_dir, IngestionConfig())
    manifest = mgr.get_manifest("markdown-text")
    assert manifest is not None
    assert manifest.name == "markdown-text"
    assert mgr._plugin_dir("markdown-text") != custom_plugin
    assert "plugin.json load failed" not in caplog.text


def test_builtin_plugin_ignores_local_shadow_manifest_and_extractor(tmp_path):
    plugins_dir = tmp_path / "plugins"
    local_builtin = plugins_dir / "pdf-pdfplumber"
    local_builtin.mkdir(parents=True)
    (local_builtin / "extractor.py").write_text("raise SystemExit(99)", encoding="utf-8")
    (local_builtin / "plugin.json").write_text(json.dumps({"name": "pdf-pdfplumber", "formats": [".evil"], "version": "9.9.9"}), encoding="utf-8")
    mgr = PluginManager(plugins_dir, IngestionConfig())
    assert mgr._plugin_dir("pdf-pdfplumber") != local_builtin
    assert mgr.get_plugin_for_format(".pdf") == "pdf-pdfplumber"
