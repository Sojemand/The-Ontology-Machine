from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import ingestion_layer_vision.orchestrator_contract as contract

from orchestrator_contract_support import DummyPluginManager


def test_debug_run_marks_session_cancelled_when_cancel_request_appears(tmp_path, monkeypatch) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    manager = DummyPluginManager({})

    class DummyCatalog:
        def __init__(self, *_args, **_kwargs):
            return None

        def refresh(self) -> bool:
            return True

        def count_after_filter(self, _filters) -> int:
            return 1

    class DummyProcessor:
        def __init__(self, *_args, **_kwargs):
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

        def process(self):
            (session_root / "cancel.request").write_text("stop", encoding="utf-8")
            deadline = time.time() + 3
            while not self.cancelled and time.time() < deadline:
                time.sleep(0.05)
            return SimpleNamespace(successful=0)

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
            "filters": {},
            "worker_count": 1,
            "hash_tools": {"use_processed_hashes": False},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))
    log_text = (session_root / "run.log").read_text(encoding="utf-8")

    assert response["status"] == "cancelled"
    assert snapshot["status"] == "cancelled"
    assert result["status"] == "cancelled"
    assert "cancel.request erkannt" in log_text
    assert "[CANCELLED] Debuglauf abgebrochen" in log_text
    assert manager.calls == ["kill_all"]
