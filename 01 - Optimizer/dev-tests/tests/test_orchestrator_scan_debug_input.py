from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import ingestion_layer_vision.orchestrator_contract as contract


def test_scan_debug_input_persists_snapshot_result_and_log(tmp_path, monkeypatch) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    session_root = tmp_path / "session"
    captured: dict[str, object] = {}
    entries = (
        SimpleNamespace(relative_path="docs/a.pdf", filename="a.pdf", extension=".pdf", size_bytes=10, content_hash="sha256:" + "ab" * 32),
        SimpleNamespace(relative_path="docs/b.png", filename="b.png", extension=".png", size_bytes=20, content_hash="sha256:" + "cd" * 32),
    )

    class DummyCatalog:
        def __init__(self, root: Path, *, state_dir=None, output_dir=None):
            captured["input_root"] = root
            captured["state_dir"] = state_dir
            captured["output_dir"] = output_dir
            self.skipped_processed_count = 1
            self.skipped_duplicate_count = 2

        def refresh(self) -> bool:
            return True

        def iter_filtered(self, _filters):
            return entries

    monkeypatch.setattr(contract, "APP_HOME", tmp_path / "app-home")
    monkeypatch.setattr("ingestion_layer_vision.orchestrator_contract.debug_processing.InputCatalog", DummyCatalog)

    response = contract._scan_debug_input(
        {
            "session_root": str(session_root),
            "input_root": str(input_root),
            "mode": "scan",
            "filters": {"format": "pdf"},
            "hash_tools": {"use_processed_hashes": True},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))
    log_text = (session_root / "run.log").read_text(encoding="utf-8")

    assert response["status"] == "ok"
    assert response["summary"] == {"pdf": 1, "png": 1}
    assert response["total_count"] == 2
    assert captured["input_root"] == input_root
    assert captured["state_dir"] is not None
    assert captured["output_dir"] == tmp_path / "app-home" / "output"
    assert snapshot["status"] == "ok"
    assert snapshot["detail"] == "2 Dateien"
    assert result["skipped_duplicate_count"] == 2
    assert result["entries"][0]["relative_path"] == "docs/a.pdf"
    assert "[SCAN] starte Input-Preview" in log_text
    assert "[SCAN] 2 Dateien im Preview" in log_text


def test_scan_debug_input_writes_error_result_for_invalid_request(tmp_path, monkeypatch) -> None:
    session_root = tmp_path / "session"
    monkeypatch.setattr(contract, "APP_HOME", tmp_path / "app-home")

    response = contract._scan_debug_input(
        {
            "session_root": str(session_root),
            "input_root": str(tmp_path / "missing"),
            "mode": "scan",
            "filters": {},
        }
    )

    snapshot = json.loads((session_root / "snapshot.json").read_text(encoding="utf-8"))
    result = json.loads((session_root / "result.json").read_text(encoding="utf-8"))

    assert response["status"] == "error"
    assert "Input-Ordner nicht gefunden" in response["error"]
    assert snapshot["status"] == "error"
    assert result["summary"] == "Scan-Debug fehlgeschlagen"
    assert "[ERROR]" in (session_root / "run.log").read_text(encoding="utf-8")
