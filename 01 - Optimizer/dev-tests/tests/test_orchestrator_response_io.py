from __future__ import annotations

import json
import threading
from pathlib import Path

import ingestion_layer_vision.orchestrator_contract as contract


def test_write_response_uses_atomic_publish(tmp_path, monkeypatch) -> None:
    response_path = tmp_path / "response.json"
    started = threading.Event()
    release = threading.Event()
    original_atomic_write = contract.atomic_json_write
    observed: dict[str, object] = {}
    errors: list[Exception] = []

    def slow_atomic_write(path: Path, payload: dict) -> None:
        started.set()
        observed["path"] = path
        observed["exists_before_publish"] = response_path.exists()
        release.wait(timeout=5)
        original_atomic_write(path, payload)

    monkeypatch.setattr(contract, "atomic_json_write", slow_atomic_write)

    def writer() -> None:
        try:
            contract._write_response(response_path, {"status": "ok"})
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=writer)
    thread.start()
    assert started.wait(timeout=5), "atomic_json_write was never reached"
    assert response_path.exists() is False
    release.set()
    thread.join(timeout=10)
    assert errors == []
    assert observed["path"] == response_path
    assert observed["exists_before_publish"] is False
    assert json.loads(response_path.read_text(encoding="utf-8")) == {"status": "ok"}
