from __future__ import annotations

from types import SimpleNamespace

from ingestion_layer_vision.input_catalog import InputCatalog
from ingestion_layer_vision.models import ExtractResult, IngestionConfig, OutputFilters
from ingestion_layer_vision.processor import Processor


class VisionPluginManager:
    def get_plugin_for_format(self, ext):
        return "pdf-plugin" if ext == ".pdf" else ("text-plugin" if ext == ".txt" else None)

    def invoke(self, plugin_name, file_path, config_override=None):
        return ExtractResult(status="success", blocks=[], metadata={}, errors=[], processing_time_ms=1)

    def get_manifest(self, plugin_name):
        return SimpleNamespace(version="1.0.0", capabilities=["text"])

    def shutdown_workers(self):
        pass

    def kill_all(self):
        pass


def apply_processor_monkeypatches(monkeypatch):
    monkeypatch.setattr("ingestion_layer_vision.processor.render_page_assets", lambda *args, **kwargs: [])


def make_processor_env(tmp_path, *, num_files=3, ext=".txt", parallel_workers=1, callback=None):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    state_dir = tmp_path / "state"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    for index in range(num_files):
        (input_dir / f"file{index}{ext}").write_text(f"Content {index}", encoding="utf-8")

    config = IngestionConfig(parallel_workers=parallel_workers, plugin_timeout_seconds=10)
    plugin_mgr = VisionPluginManager()
    input_catalog = InputCatalog(input_dir, state_dir=state_dir, output_dir=output_dir)
    input_catalog.refresh()
    proc = Processor(config, plugin_mgr, input_catalog, OutputFilters(), output_dir, callback=callback)
    return proc, input_dir, output_dir, state_dir, config, plugin_mgr, input_catalog


def make_empty_processor(tmp_path):
    proc, *_ = make_processor_env(tmp_path, num_files=0)
    return proc
