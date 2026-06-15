from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orchestrator.debug_host.types import DebugPlan, DebugResult, DebugStep
from orchestrator.ui import debug_rendering


def debug_plan_for(module_key: str, mode: str, **_kwargs) -> DebugPlan:
    if module_key == "interpreter":
        return DebugPlan(mode, (DebugStep.module("optimizer", "debug_run"), DebugStep.host("request_enrichment"), DebugStep.module("interpreter", "debug_run")))
    if module_key == "validator":
        return DebugPlan(mode, (DebugStep.module("validator", "debug_run"),))
    if module_key == "optimizer":
        action = "scan_debug_input" if mode == "scan" else "debug_run"
        return DebugPlan(mode, (DebugStep.module("optimizer", action),))
    if module_key == "normalizer":
        return DebugPlan(mode, (DebugStep.module("normalizer", "debug_run"),))
    if module_key == "corpus_builder":
        action = "scan_debug_input" if mode == "scan" else "debug_run"
        return DebugPlan(mode, (DebugStep.module("corpus_builder", action),))
    raise AssertionError(f"unexpected module: {module_key}")


def single_step_plan(module_key: str, mode: str, **_kwargs) -> DebugPlan:
    return DebugPlan(mode, (DebugStep.module(module_key, "debug_run"),))


def session(session_root: Path, output_root: Path, result: DebugResult) -> SimpleNamespace:
    return SimpleNamespace(
        active_step=None,
        session_root=session_root,
        output_root=output_root,
        request_path=session_root / "request.json",
        response_path=session_root / "response.json",
        snapshot_path=session_root / "snapshot.json",
        result_path=session_root / "result.json",
        run_log_path=session_root / "run.log",
        snapshot=None,
        result=result,
    )


def assert_validator_batch_controls(app, tmp_path: Path) -> None:
    app._debug_module_var.set("validator")
    app._debug_mode_var.set("batch")
    app._debug_input_entry.insert(0, str(tmp_path / "structured"))
    app._debug_raw_root_entry.insert(0, str(tmp_path / "raw"))
    app._debug_artifact_import_entry.insert(0, str(tmp_path / "artifacts"))
    debug_rendering.apply_view(app)

    assert app._debug_console_cards["advanced"].visible is True
    assert app._debug_control_rows["input_path"].visible is True
    assert app._debug_control_rows["source_path"].visible is False
    assert all(app._debug_control_rows[key].visible is True for key in ("raw_path", "raw_root", "check_toggles"))
    assert "Replay path without readable artifacts" in app._debug_replay_status_label.value
    assert app._debug_help_btn.config["state"] == "normal"


def assert_optimizer_scan_controls(app) -> None:
    app._debug_module_var.set("optimizer")
    app._debug_mode_var.set("scan")
    debug_rendering.apply_view(app)

    assert app._debug_help_btn.config["state"] == "normal"
    assert app._debug_console_cards["advanced"].visible is True
    assert app._debug_control_rows["input_path"].visible is True
    assert app._debug_control_rows["source_path"].visible is False
    assert all(app._debug_control_rows[key].visible is True for key in ("format", "doc_type", "max_size_mb", "batch_size", "worker_count", "hash_tools"))


def assert_normalizer_batch_controls(app, tmp_path: Path) -> None:
    app._debug_module_var.set("normalizer")
    app._debug_mode_var.set("batch")
    app._debug_input_entry.insert(0, str(tmp_path / "structured"))
    debug_rendering.apply_view(app)

    assert "normalizer:debug_run" in app._debug_plan_label.value
    assert app._debug_console_cards["advanced"].visible is True
    assert app._debug_control_rows["input_path"].visible is True
    assert app._debug_control_rows["source_path"].visible is False
    assert app._debug_control_rows["worker_count"].visible is True
    assert all(app._debug_control_rows[key].visible is False for key in ("format", "hash_tools", "raw_path"))


def assert_corpus_builder_single_controls(app, tmp_path: Path) -> None:
    app._debug_module_var.set("corpus_builder")
    app._debug_mode_var.set("single")
    app._debug_input_entry.delete(0, "end")
    app._debug_input_entry.insert(0, str(tmp_path / "normalized" / "invoice.structured.normalized.json"))
    debug_rendering.apply_view(app)

    assert "corpus_builder:debug_run" in app._debug_plan_label.value
    assert app._debug_console_cards["advanced"].visible is True
    assert app._debug_control_rows["input_path"].visible is True
    assert app._debug_control_rows["source_path"].visible is False
    assert app._debug_control_rows["persist_page_images"].visible is True
    assert all(app._debug_control_rows[key].visible is False for key in ("format", "worker_count", "raw_path"))
    assert app._debug_mode_menu.config["state"] == "normal"
    assert app._debug_help_btn.config["state"] == "normal"
