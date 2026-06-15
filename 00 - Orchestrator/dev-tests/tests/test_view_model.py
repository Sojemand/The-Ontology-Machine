from __future__ import annotations

from orchestrator.models import PipelineSnapshot, StageSnapshot, UiState
from orchestrator.state import load_ui_state, save_ui_state
from orchestrator.ui import theme
from orchestrator.ui import view_model


def test_ui_state_persists_paths_and_mode(tmp_path) -> None:
    path = tmp_path / "ui_state.json"
    state = UiState(
        input_folder="in",
        artifact_folder="artifacts",
        corpus_output_folder="corp",
        mode="single",
    )
    save_ui_state(path, state)
    loaded = load_ui_state(path)
    assert loaded.mode == "single"
    assert loaded.artifact_folder == "artifacts"


def test_view_model_button_state_progress_and_log_formatting() -> None:
    snapshot = PipelineSnapshot(
        total=4,
        completed=2,
        pending=1,
        success=2,
        errors=1,
        needs_review=0,
        retries=3,
        current_file="doc.pdf",
        current_attempt=2,
        current_route_family="Documents",
        current_optimizer_module="Optimizer",
        current_interpreter_module="Interpreter",
        current_intake_reason="Born-digital PDF detected.",
        stage_statuses={
            "Intake": StageSnapshot(status="Done", detail="Documents | Optimizer | Interpreter | Born-digital PDF detected."),
            "Runtime Semantics": StageSnapshot(status="Done", detail="semantic_release.default | 1 | sha256:semantic"),
            "Optimizer": StageSnapshot(status="Done", detail="Documents | Optimizer | raw"),
            "Request Enrichment": StageSnapshot(status="Done", detail="interpreter.request.json"),
            "Interpreter": StageSnapshot(status="Review", detail="check", progress_current=2, progress_total=5, progress_label="Requests"),
            "Validator": StageSnapshot(status="Ready", detail=""),
            "Normalizer": StageSnapshot(status="Ready", detail="", progress_current=1, progress_total=5, progress_label="Requests"),
            "Corpus Builder": StageSnapshot(status="Ready", detail=""),
            "Embeddings": StageSnapshot(status="Done", detail="1 embeddings generated."),
        },
    )
    assert view_model.progress_value(snapshot) == 0.5
    assert view_model.counter_values(snapshot)["Retries"] == "3"
    assert "doc.pdf" in view_model.status_line(snapshot)
    assert view_model.stage_values(snapshot)["Interpreter"] == ("Review", "check")
    assert view_model.stage_progress_text(snapshot.stage_statuses["Interpreter"]) == "2/5 Requests"
    assert view_model.stage_progress_text(snapshot.stage_statuses["Validator"]) == ""
    assert view_model.route_values(snapshot)["Route Family"] == "Documents"
    assert view_model.route_values(snapshot)["Optimizer"] == "Optimizer"
    assert view_model.format_log_line("hello") == "hello\n"


def test_status_line_handles_aborted_and_initializing_snapshots() -> None:
    aborted = PipelineSnapshot(current_file="doc.pdf", current_attempt=2, aborted=True)
    initializing = PipelineSnapshot(is_running=True)
    ready = PipelineSnapshot()

    assert view_model.status_line(aborted) == "Aborted | File: doc.pdf | Attempt: 2"
    assert view_model.status_line(initializing) == "Initializing..."
    assert view_model.status_line(ready) == theme.STATUS_READY


def test_stage_text_color_maps_runtime_statuses_to_theme_colors() -> None:
    assert view_model.stage_text_color(theme.STATUS_READY) == theme.COLOR_TEXT
    assert view_model.stage_text_color(theme.STATUS_DONE) == theme.COLOR_SUCCESS
    assert view_model.stage_text_color(theme.STATUS_ERROR) == theme.COLOR_ERROR
    assert view_model.stage_text_color("Review") == theme.COLOR_WARNING
    assert view_model.stage_text_color("Processing...") == theme.COLOR_WARNING
    assert view_model.stage_text_color("Aborted") == theme.COLOR_WARNING
    assert view_model.stage_text_color("WARN") == theme.COLOR_WARNING
    assert view_model.stage_text_color("loaded") == theme.COLOR_SUCCESS
    assert view_model.stage_text_color("FAIL") == theme.COLOR_ERROR


def test_compact_stage_detail_normalizes_and_truncates() -> None:
    assert view_model.compact_stage_detail(" short   detail ") == "short detail"
    assert view_model.compact_stage_detail("x" * 90, limit=20) == ("x" * 17) + "..."


def test_status_line_color_maps_snapshot_outcomes_to_theme_colors() -> None:
    assert view_model.status_line_color(PipelineSnapshot()) == theme.COLOR_TEXT
    assert view_model.status_line_color(PipelineSnapshot(is_running=True)) == theme.COLOR_WARNING
    assert view_model.status_line_color(PipelineSnapshot(aborted=True)) == theme.COLOR_WARNING
    assert view_model.status_line_color(PipelineSnapshot(errors=1)) == theme.COLOR_ERROR
    assert view_model.status_line_color(PipelineSnapshot(needs_review=1)) == theme.COLOR_WARNING
    assert (
        view_model.status_line_color(PipelineSnapshot(total=2, completed=2, success=2))
        == theme.COLOR_SUCCESS
    )

