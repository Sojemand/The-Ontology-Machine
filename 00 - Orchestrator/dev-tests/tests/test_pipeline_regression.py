from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.pipeline import OrchestratorEngine
from tests.pipeline_regression_fixtures import (
    CASE_NAMES,
    FIXTURES_ROOT,
    FixtureReplayModules,
    assert_regression_case,
    load_regression_record,
    make_regression_ui_state,
    read_json,
)


@pytest.mark.parametrize("case_name", CASE_NAMES)
def test_pipeline_regression_cases(tmp_path: Path, case_name: str) -> None:
    case_dir = FIXTURES_ROOT / case_name
    case = read_json(case_dir / "case.json")
    ui_state = make_regression_ui_state(tmp_path, case_dir)
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FixtureReplayModules(case_dir, case))
    try:
        summary = engine.run(ui_state)
    finally:
        engine.close()
    assert_regression_case(case, ui_state, summary, load_regression_record(ui_state))


def test_pipeline_regression_reset_roundtrip(tmp_path: Path) -> None:
    case_dir = FIXTURES_ROOT / "validator_fail"
    case = read_json(case_dir / "case.json")
    ui_state = make_regression_ui_state(tmp_path, case_dir)
    engine = OrchestratorEngine(orchestrator_root=tmp_path / "orchestrator", modules=FixtureReplayModules(case_dir, case))
    try:
        engine.run(ui_state)
        summary = engine.reset_run_history(ui_state)
    finally:
        engine.close()
    expected = case["expected_reset"]
    assert summary.cleared_records == expected["cleared_records"]
    assert summary.restored_sources == expected["restored_sources"]
    assert summary.renamed_conflicts == expected["renamed_conflicts"]
    assert summary.removed_targets >= expected["min_removed_targets"]
    if expected.get("source_restored"):
        assert (Path(ui_state.input_folder) / expected["source_restored"]).exists()
    for rel_path in expected["removed_artifact_paths"]:
        assert not (Path(ui_state.artifact_folder) / rel_path).exists()
    for rel_path in expected["removed_corpus_files"]:
        assert not (Path(ui_state.corpus_output_folder) / rel_path).exists()
