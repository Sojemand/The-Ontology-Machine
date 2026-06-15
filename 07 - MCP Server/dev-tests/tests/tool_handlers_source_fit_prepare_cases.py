from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool
from mcp_server.tool_visibility import kernel_syscall_context

from .tool_handlers_source_fit_support import _write_json


def test_prepare_source_samples_for_input_copies_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_root = tmp_path / "Input"
    artifact_root = tmp_path / "Artifacts"
    corpus_root = artifact_root / "Corpus"
    orchestrator_root = tmp_path / "Orchestrator"
    input_root.mkdir()
    corpus_root.mkdir(parents=True)
    db_path = corpus_root / "active.db"
    db_path.write_bytes(b"")
    source = tmp_path / "Samples" / "story.txt"
    source.parent.mkdir()
    source.write_text("new sample", encoding="utf-8")
    conflict = input_root / "story.txt"
    conflict.write_text("different file", encoding="utf-8")
    ui_state_path = orchestrator_root / "state" / "ui_state.json"
    _write_json(
        ui_state_path,
        {
            "input_folder": str(input_root),
            "artifact_folder": str(artifact_root),
            "corpus_output_folder": str(corpus_root),
            "selected_corpus_db_path": str(db_path),
            "semantic_release_mode": "database_default",
        },
    )
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=orchestrator_root))
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)

    with kernel_syscall_context():
        result = call_tool(
            "prepare_source_samples_for_input",
            {"source_document_paths": [str(source)], "user_confirmed": True},
        )

    assert conflict.read_text(encoding="utf-8") == "different file"
    queued = next(input_root.glob("story.sample-*.txt"))
    assert queued.read_text(encoding="utf-8") == "new sample"
    assert result["sample_input_summary"]["copied"] == 1
    assert Path(result["manifest_path"]).exists()
