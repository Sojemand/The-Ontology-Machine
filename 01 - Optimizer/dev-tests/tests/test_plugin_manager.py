"""Tests for the slim built-in extractor runtime."""
from __future__ import annotations

from ingestion_layer_vision.models import IngestionConfig
from ingestion_layer_vision.plugin_manager import PluginManager


def test_builtin_extractors_load_from_bundled_plugins(tmp_path):
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())

    names = [manifest.name for manifest in mgr.list_plugins()]
    assert names == ["markdown-text", "pdf-pdfplumber"]


def test_builtin_format_routing_covers_text_pdf_and_images(tmp_path):
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())

    assert mgr.get_plugin_for_format(".txt") == "markdown-text"
    assert mgr.get_plugin_for_format(".pdf") == "pdf-pdfplumber"
    assert mgr.get_plugin_for_format(".pdf:scanned") is None
    assert mgr.get_plugin_for_format(".png") is None
    assert mgr.get_plugin_for_format(".xyz") is None


def test_markdown_selftest_runs_without_custom_registry(tmp_path):
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())

    ok, msg = mgr.selftest("markdown-text")

    assert ok is True
    assert "OK" in msg

def test_llm_ocr_is_not_registered_as_a_local_plugin(tmp_path):
    mgr = PluginManager(tmp_path / "plugins", IngestionConfig())

    assert mgr.get_manifest("optimizer-llm-ocr") is None
    assert [manifest.name for manifest in mgr.list_plugins()] == ["markdown-text", "pdf-pdfplumber"]

