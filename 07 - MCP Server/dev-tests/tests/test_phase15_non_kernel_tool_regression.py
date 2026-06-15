from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_representative_non_kernel_tools_still_dispatch_after_legacy_unlink(monkeypatch, tmp_path: Path) -> None:
    orchestrator_root = tmp_path / "Orchestrator"
    input_root = tmp_path / "Input"
    artifact_root = tmp_path / "Artifacts"
    corpus_root = artifact_root / "Corpus"
    db_path = corpus_root / "active.db"
    input_root.mkdir()
    corpus_root.mkdir(parents=True)
    db_path.write_bytes(b"")
    (input_root / "story.txt").write_text("sample", encoding="utf-8")
    ui_state_path = orchestrator_root / "state" / "ui_state.json"
    _write_json(
        ui_state_path,
        {
            "input_folder": str(input_root),
            "artifact_folder": str(artifact_root),
            "corpus_output_folder": str(corpus_root),
            "selected_corpus_db_path": str(db_path),
        },
    )

    product_calls: list[tuple[str, dict]] = []
    admin_calls: list[tuple[str, dict]] = []

    def fake_product(module_key: str, payload: dict) -> dict:
        product_calls.append((module_key, dict(payload)))
        if payload.get("action") == "search":
            return {"status": "ok", "matches": [], "result_count": 0}
        raise AssertionError(f"Unexpected product payload: {module_key} {payload}")

    def fake_admin(module_key: str, payload: dict) -> dict:
        admin_calls.append((module_key, dict(payload)))
        if payload.get("action") == "inspect_runtime":
            return {"status": "ok", "runtime_settings": {}, "runtime_python": "runtime/python/python.exe"}
        raise AssertionError(f"Unexpected admin payload: {module_key} {payload}")

    monkeypatch.setattr(tool_handlers, "_invoke_product", fake_product)
    monkeypatch.setattr(tool_handlers, "_invoke_admin", fake_admin)
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=orchestrator_root))
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)

    health = call_tool("mcp_server.healthcheck", {})
    environment = call_tool("inspect_current_environment_status", {})
    search = call_tool("search_corpus", {"query": "story"})
    runtime = call_tool("inspect_runtime", {})

    assert health["status"] == "ok"
    assert environment["database_present"] is True
    assert environment["input_file_count"] == 1
    assert search["status"] == "ok"
    assert runtime["status"] == "ok"
    assert product_calls == [("corpus_builder", {"action": "search", "query": "story", "mode": "Fulltext"})]
    assert admin_calls == [("orchestrator", {"action": "inspect_runtime"})]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
