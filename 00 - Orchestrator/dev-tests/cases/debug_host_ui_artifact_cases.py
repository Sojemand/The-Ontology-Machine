from __future__ import annotations

from pathlib import Path

from orchestrator.debug_host.types import DebugResult
from orchestrator.ui import debug_rendering

from cases.debug_host_ui_rendering_support import session, single_step_plan
from support.debug_host_ui_support_impl import make_app


def test_debug_rendering_keeps_corpus_builder_session_db_visible_and_preview_safe(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_module_var.set("corpus_builder")
    app._debug_mode_var.set("single")
    normalized_path = tmp_path / "normalized" / "invoice.structured.normalized.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text("{}", encoding="utf-8")
    app._debug_input_entry.insert(0, str(normalized_path))
    session_root = tmp_path / "session"
    output_root = session_root / "outputs"
    corpus_db_path = output_root / "corpus.db"
    preview_path = output_root / "preview_report.json"
    load_path = output_root / "load_report.json"
    for path, payload in (
        (session_root / "request.json", "{}"),
        (session_root / "response.json", "{}"),
        (session_root / "snapshot.json", "{}"),
        (session_root / "result.json", "{}"),
        (session_root / "run.log", "started\n"),
        (preview_path, '{"bundle_count":1}'),
        (load_path, '{"loaded":1}'),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    corpus_db_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_db_path.write_bytes(b"SQLite format 3\x00session")
    app._debug_session = session(session_root, output_root, DebugResult(status="ok", summary="done", outputs={
        "corpus_db": [str(corpus_db_path.relative_to(session_root).as_posix())],
        "preview_report": [str(preview_path.relative_to(session_root).as_posix())],
        "load_report": [str(load_path.relative_to(session_root).as_posix())],
    }))
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", single_step_plan)

    debug_rendering.apply_view(app)

    names = {entry.path.name for entry in app._debug_artifact_entries}
    assert {
        "request.json",
        "response.json",
        "snapshot.json",
        "result.json",
        "run.log",
        "corpus.db",
        "preview_report.json",
        "load_report.json",
    }.issubset(names)

    app._selected_debug_artifact_index = next(
        index for index, entry in enumerate(app._debug_artifact_entries) if entry.path.name == "corpus.db"
    )
    debug_rendering.apply_view(app)

    assert "SQLite database artifact." in app._debug_preview_box.value
    assert "Inline preview is not available." in app._debug_preview_box.value


def test_corpus_builder_replay_import_includes_sqlite_and_preview_is_safe(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    app._debug_module_var.set("corpus_builder")
    app._debug_mode_var.set("batch")
    input_root = tmp_path / "normalized"
    input_root.mkdir(parents=True, exist_ok=True)
    app._debug_input_entry.insert(0, str(input_root))
    replay_root = tmp_path / "replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    corpus_db_path = replay_root / "corpus.db"
    corpus_db_path.write_bytes(b"SQLite format 3\x00test")
    (replay_root / "preview_report.json").write_text('{"bundle_count":1}', encoding="utf-8")
    (replay_root / "load_report.json").write_text('{"loaded":1}', encoding="utf-8")
    monkeypatch.setattr("orchestrator.ui.debug_rendering.plan_for", single_step_plan)

    app._debug_artifact_import_entry.insert(0, str(replay_root))
    debug_rendering.apply_view(app)

    names = {entry.path.name for entry in app._debug_artifact_entries}
    assert {"corpus.db", "preview_report.json", "load_report.json"}.issubset(names)

    app._selected_debug_artifact_index = next(
        index for index, entry in enumerate(app._debug_artifact_entries) if entry.path.name == "corpus.db"
    )
    debug_rendering.apply_view(app)

    assert "SQLite database artifact." in app._debug_preview_box.value
    assert "Inline preview is not available." in app._debug_preview_box.value
    assert "Open Artifacts" in app._debug_preview_box.value
