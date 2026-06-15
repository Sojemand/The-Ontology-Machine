from __future__ import annotations

from pathlib import Path

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_fake_modules import FakeModules
from tests.pipeline_harness import create_source, make_ui_state


def test_pipeline_emits_in_progress_snapshots_for_interpreter_validator_and_corpus(tmp_path: Path) -> None:
    ui_state = make_ui_state(tmp_path)
    create_source(ui_state)
    snapshots: list[dict[str, object]] = []
    engine = OrchestratorEngine(
        orchestrator_root=tmp_path / "orchestrator",
        modules=FakeModules({}),
        snapshot_callback=lambda snapshot: snapshots.append(snapshot.to_dict()),
    )

    summary = engine.run(ui_state)

    assert summary.success == 1
    assert any(
        entry["stage_statuses"]["Request Enrichment"]["status"] == "Processing..."
        and entry["stage_statuses"]["Request Enrichment"]["detail"] == "Documents | doc.pdf.raw.json"
        for entry in snapshots
    )
    assert any(
        entry["stage_statuses"]["Interpreter"]["status"] == "Processing..."
        and entry["stage_statuses"]["Interpreter"]["detail"] == "Documents | Interpreter | interpreter.request.json"
        and entry["stage_statuses"]["Interpreter"]["progress_current"] == 0
        and entry["stage_statuses"]["Interpreter"]["progress_total"] == 1
        and entry["stage_statuses"]["Interpreter"]["progress_label"] == "Pages"
        for entry in snapshots
    )
    assert any(
        entry["stage_statuses"]["Validator"]["status"] == "Processing..."
        and str(entry["stage_statuses"]["Validator"]["detail"]).endswith(".structured.json")
        for entry in snapshots
    )
    assert any(
        entry["stage_statuses"]["Normalizer"]["status"] == "Processing..."
        and str(entry["stage_statuses"]["Normalizer"]["detail"]).endswith(".structured.json")
        and entry["stage_statuses"]["Normalizer"]["progress_current"] == 0
        and entry["stage_statuses"]["Normalizer"]["progress_total"] == 1
        and entry["stage_statuses"]["Normalizer"]["progress_label"] == "Pages"
        for entry in snapshots
    )
    assert any(
        entry["stage_statuses"]["Corpus Builder"]["status"] == "Processing..."
        and str(entry["stage_statuses"]["Corpus Builder"]["detail"]).endswith(".structured.normalized.json")
        for entry in snapshots
    )
