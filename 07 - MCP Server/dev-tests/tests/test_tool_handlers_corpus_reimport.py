from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_prepare_reimport_selects_only_active_db_originals_and_preserves_extras(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _reimport_fixture(tmp_path, monkeypatch)

    preview = call_tool("preview_active_corpus_source_reimport", {})

    assert preview["reimport_plan"]["selected_for_reimport"] == 1
    assert preview["reimport_plan"]["originals_total_files"] == 2
    assert preview["entries_preview"][0]["pipeline_relative_path"] == "nested/story.txt"

    prepared = call_tool("prepare_active_corpus_source_reimport", {"user_confirmed": True})

    queued = paths["input"] / "nested" / "story.txt"
    assert queued.read_text(encoding="utf-8") == "old story"
    assert (paths["originals"] / "nested" / "story.txt").exists()
    assert not (paths["input"] / "unrelated.txt").exists()
    assert prepared["reimport_summary"]["copied"] == 1
    manifest = Path(prepared["manifest_path"])
    assert manifest.exists()
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["entries"][0]["apply_status"] == "copied"


def test_prepare_reimport_renames_input_conflicts_without_overwriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _reimport_fixture(tmp_path, monkeypatch)
    conflict = paths["input"] / "nested" / "story.txt"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("new incoming file", encoding="utf-8")

    prepared = call_tool("prepare_active_corpus_source_reimport", {"user_confirmed": True})

    assert conflict.read_text(encoding="utf-8") == "new incoming file"
    renamed = next(path for path in (paths["input"] / "nested").glob("story.reimport-*.txt"))
    assert renamed.read_text(encoding="utf-8") == "old story"
    assert prepared["reimport_summary"]["copied"] == 1
    assert prepared["entries_preview"][0]["status"] == "rename_conflict"


def test_prepare_reimport_roundtrips_actual_originals_archive_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _reimport_fixture(
        tmp_path,
        monkeypatch,
        original_relative_path="nested/story__archive_abcd1234.txt",
        record_relative_path="nested/story.txt",
    )

    prepared = call_tool("prepare_active_corpus_source_reimport", {"user_confirmed": True})

    queued = paths["input"] / "nested" / "story__archive_abcd1234.txt"
    assert queued.read_text(encoding="utf-8") == "old story"
    assert not (paths["input"] / "nested" / "story.txt").exists()
    assert prepared["entries_preview"][0]["target_relative_path"] == "nested/story__archive_abcd1234.txt"


def _reimport_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    original_relative_path: str = "nested/story.txt",
    record_relative_path: str = "nested/story.txt",
) -> dict[str, Path]:
    orchestrator_root = tmp_path / "Orchestrator"
    state_root = orchestrator_root / "state"
    input_root = tmp_path / "Artifacts" / "Input"
    artifact_root = tmp_path / "Artifacts"
    corpus_root = artifact_root / "Corpus"
    originals_root = artifact_root / "Documents" / "originals"
    input_root.mkdir(parents=True)
    corpus_root.mkdir(parents=True)
    originals_root.mkdir(parents=True)
    db_path = corpus_root / "active.db"
    old_source = originals_root / original_relative_path
    old_source.parent.mkdir(parents=True)
    old_source.write_text("old story", encoding="utf-8")
    unrelated = originals_root / "unrelated.txt"
    unrelated.write_text("not in this DB", encoding="utf-8")
    content_hash = _sha256(old_source)
    _write_db(db_path, content_hash)
    ui_state = {
        "input_folder": str(input_root),
        "artifact_folder": str(artifact_root),
        "corpus_output_folder": str(corpus_root),
        "selected_corpus_db_path": str(db_path),
        "semantic_release_mode": "database_default",
    }
    ui_state_path = state_root / "ui_state.json"
    _write_json(ui_state_path, ui_state)
    _write_json(
        state_root / "pipeline" / "pipeline_state.json",
        {
            "version": 1,
            "documents": {
                content_hash: {
                    "content_hash": content_hash,
                    "file_name": "story.txt",
                    "relative_path": record_relative_path,
                    "original_source_path": str(input_root / "nested" / "story.txt"),
                    "source_path": str(old_source),
                    "current_location": "originals_archive",
                    "status": "loaded",
                    "final_disposition": "success",
                    "artifacts": {},
                }
            },
        },
    )
    monkeypatch.setattr(tool_handlers, "module_spec", lambda _module_key: SimpleNamespace(root=orchestrator_root))
    monkeypatch.setattr(tool_handlers, "_orchestrator_ui_state_path", lambda: ui_state_path)
    return {"input": input_root, "artifact": artifact_root, "originals": originals_root, "db": db_path}


def _write_db(path: Path, content_hash: str) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, is_archived BOOLEAN DEFAULT 0)")
        conn.execute("INSERT INTO documents (id, content_hash, is_archived) VALUES (?, ?, 0)", ("doc-1", content_hash))
        conn.commit()
    finally:
        conn.close()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
