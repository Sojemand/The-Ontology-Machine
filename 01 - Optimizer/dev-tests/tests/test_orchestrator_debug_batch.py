from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import ingestion_layer_vision.orchestrator_contract as contract
from orchestrator_contract_support import DummyPluginManager


def test_debug_run_batch_uses_catalog_and_progress_callback(tmp_path, monkeypatch) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    manager = DummyPluginManager({})
    captured: dict[str, object] = {}

    class DummyCatalog:
        def __init__(self, root: Path, *, state_dir=None, output_dir=None):
            captured["catalog_root"] = root
            captured["state_dir"] = state_dir
            captured["output_dir"] = output_dir

        def refresh(self) -> bool:
            return True

        def count_after_filter(self, _filters) -> int:
            return 2

    class DummyProcessor:
        def __init__(self, config, _plugin_mgr, catalog, filters, root, callback=None):
            captured["config"] = config
            captured["catalog"] = catalog
            captured["filters"] = filters
            captured["callback"] = callback
            self._output_root = root

        def process(self):
            raw_path = self._output_root / "raw_extracts" / "batch" / "a.raw.json"
            image_path = self._output_root / "page_assets" / "batch" / "a" / "page_001.png"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("{}", encoding="utf-8")
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_text("png", encoding="utf-8")
            captured["callback"](
                SimpleNamespace(
                    current_file="batch/a.pdf",
                    total_files_processed=2,
                    total_extracts_written=1,
                    total_images_rendered=1,
                )
            )
            return SimpleNamespace(successful=2)

        def cancel(self) -> None:
            captured["cancelled"] = True

    monkeypatch.setattr(contract, "APP_HOME", tmp_path / "app-home")
    monkeypatch.setattr(contract, "load_config", lambda _path: SimpleNamespace(parallel_workers=0))
    monkeypatch.setattr(contract, "PluginManager", lambda *_args, **_kwargs: manager)
    monkeypatch.setattr(contract, "Processor", DummyProcessor)
    monkeypatch.setattr("ingestion_layer_vision.orchestrator_contract.debug_processing.InputCatalog", DummyCatalog)

    response = contract._debug_run(
        {
            "session_root": str(session_root),
            "input_root": str(input_root),
            "output_root": str(output_root),
            "mode": "batch",
            "filters": {"doc_type": "invoice", "batch_size": 0},
            "worker_count": 2,
            "hash_tools": {"use_processed_hashes": True},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))

    assert response["status"] == "ok"
    assert response["outputs"]["raw_extracts"] == ["outputs/raw_extracts/batch/a.raw.json"]
    assert response["outputs"]["page_assets"] == ["outputs/page_assets/batch/a/page_001.png"]
    assert captured["catalog_root"] == input_root
    assert captured["state_dir"] is not None
    assert captured["filters"].doc_type == "invoice"
    assert captured["config"].parallel_workers == 2
    assert snapshot["status"] == "ok"
    assert snapshot["processed"] == 2
    assert manager.calls == ["kill_all"]
