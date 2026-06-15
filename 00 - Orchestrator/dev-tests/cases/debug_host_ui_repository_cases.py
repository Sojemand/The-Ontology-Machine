from __future__ import annotations

import json
from pathlib import Path

from orchestrator.ui import debug_repository
from orchestrator.ui.debug_actions import DebugHostAppActions

from support.debug_host_ui_support_impl import make_app


def test_debug_repository_roundtrip_and_runtime_options(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    restored = debug_repository.restore_state(app)
    assert (restored["module_key"], restored["mode"]) == ("optimizer", "scan")

    app._debug_module_var.set("Interpreter")
    app._debug_mode_var.set("single")
    app._debug_source_entry.insert(0, "incoming/invoice.pdf")
    app._debug_format_entry.insert(0, "pdf")
    app._debug_worker_entry.insert(0, "4")
    debug_repository.save_state(app)
    app._debug_source_entry.delete(0, "end")
    restored = debug_repository.restore_state(app)

    assert (restored["module_key"], restored["mode"], restored["source_path"]) == (
        "interpreter",
        "single",
        "incoming/invoice.pdf",
    )
    assert app._debug_module_menu.value == "Interpreter"
    assert debug_repository.runtime_options(restored, descriptor=app._debug_descriptors["interpreter"]) == {}
    assert debug_repository.runtime_options(restored, descriptor=app._debug_descriptors["optimizer"])["worker_count"] == 4
    persisted = json.loads(app._debug_state_path.read_text(encoding="utf-8"))
    assert persisted["artifact_import_path"] == ""

    app._debug_module_var.set("validator")
    app._debug_mode_var.set("batch")
    app._debug_input_entry.insert(0, str(tmp_path / "structured"))
    app._debug_raw_root_entry.insert(0, str(tmp_path / "raw"))
    debug_repository.save_state(app)
    restored = debug_repository.restore_state(app)

    assert restored["input_path"] == str(tmp_path / "structured")
    assert debug_repository.runtime_options(restored, descriptor=app._debug_descriptors["validator"]) == {
        "raw_evidence": {"raw_path": None, "raw_root": str(tmp_path / "raw")},
        "check_toggles": {"free_text": True, "context_scalars": True, "content_fields": True, "rows": True},
    }


def test_restore_state_strips_legacy_replay_import_from_persisted_state(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    app._debug_state_path.parent.mkdir(parents=True, exist_ok=True)
    app._debug_state_path.write_text(
        '{"module_key":"interpreter","mode":"single","artifact_import_path":"C:/legacy/stuck.json","dismissed_artifact_paths":[]}',
        encoding="utf-8",
    )

    restored = debug_repository.restore_state(app)
    persisted = json.loads(app._debug_state_path.read_text(encoding="utf-8"))

    assert restored["artifact_import_path"] == ""
    assert app._debug_artifact_import_entry.value == ""
    assert persisted["artifact_import_path"] == ""


def test_browse_debug_input_uses_module_specific_single_file_filters(tmp_path: Path, monkeypatch) -> None:
    app = make_app(tmp_path)
    validator_capture: dict[str, object] = {}
    corpus_capture: dict[str, object] = {}

    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.dialogs.select_debug_input_path",
        lambda _app, **kwargs: validator_capture.update(kwargs) or "",
    )
    app._debug_module_var.set("validator")
    app._debug_mode_var.set("single")

    DebugHostAppActions._browse_debug_input(app)

    assert validator_capture == {
        "select_file": True,
        "title": "Select Structured Input File",
        "filetypes": (
            ("Structured JSON", "*.structured.json"),
            ("JSON", "*.json"),
            ("All files", "*.*"),
        ),
    }

    monkeypatch.setattr(
        "orchestrator.ui.debug_actions.dialogs.select_debug_input_path",
        lambda _app, **kwargs: corpus_capture.update(kwargs) or "",
    )
    app._debug_module_var.set("corpus_builder")
    app._debug_mode_var.set("single")

    DebugHostAppActions._browse_debug_input(app)

    assert corpus_capture == {
        "select_file": True,
        "title": "Select Normalized Input File",
        "filetypes": (
            ("Structured Normalized JSON", "*.structured.normalized.json"),
            ("JSON", "*.json"),
            ("All files", "*.*"),
        ),
    }


def test_debug_launch_paths_ignore_main_input_for_optimizer_single(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    selected_source = tmp_path / "Storage" / "Image" / "scan.pdf"
    selected_source.parent.mkdir(parents=True, exist_ok=True)
    selected_source.write_text("pdf", encoding="utf-8")
    app._input_entry.insert(0, str(tmp_path / "Artefacts Test 03" / "Input"))
    app._debug_module_var.set("optimizer")
    app._debug_mode_var.set("single")
    app._debug_source_entry.insert(0, str(selected_source))

    state = debug_repository.read_state(app)
    descriptor = debug_repository.descriptor_for_state(app, state)
    input_root, source_path = DebugHostAppActions._debug_launch_paths(app, state, descriptor)

    assert Path(input_root) == selected_source.parent
    assert source_path == str(selected_source)


def test_debug_launch_paths_use_debug_input_for_optimizer_batch(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    debug_input = tmp_path / "Debug Input"
    debug_input.mkdir()
    app._input_entry.insert(0, str(tmp_path / "Kernel State" / "Input"))
    app._debug_module_var.set("optimizer")
    app._debug_mode_var.set("batch")
    app._debug_input_entry.insert(0, str(debug_input))

    state = debug_repository.read_state(app)
    descriptor = debug_repository.descriptor_for_state(app, state)
    input_root, source_path = DebugHostAppActions._debug_launch_paths(app, state, descriptor)

    assert input_root == str(debug_input)
    assert source_path == ""
