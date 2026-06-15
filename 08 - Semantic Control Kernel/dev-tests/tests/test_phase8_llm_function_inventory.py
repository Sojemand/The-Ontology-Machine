from __future__ import annotations

import json
from pathlib import Path

from semantic_control_kernel.workflows.llm_calls.function_registry import (
    REPORT_TEXT,
    get_llm_function_registry,
)


MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_phase8_drift_preflight_records_build_plan_authority() -> None:
    payload = json.loads((MODULE_ROOT / "dev-tests" / "fixtures" / "llm_calls" / "phase8_drift_preflight.json").read_text())

    assert payload["drift_preflight"] == "build_plan_authority_applied"
    assert any("semantic_control_kernel_llm" in drift["build_plan_detail"] for drift in payload["drifts"])


def test_registry_contains_exact_phase8_llm_inventory() -> None:
    registry = get_llm_function_registry()

    assert tuple(registry) == (
        "analyze_samples",
        "user_report_samples",
        "create_taxonomy_to_sample_analyses",
        "create_projections_to_sample_analyses",
    )
    assert registry["analyze_samples"].input_contract == "array[kernel.analyze_sample.input.v1]"
    assert registry["analyze_samples"].output_contract == "kernel.sample_analyses.v1"
    assert registry["analyze_samples"].run_folder_template == "sa/{analysis_run_id}"
    assert registry["create_taxonomy_to_sample_analyses"].downstream_consumers == ("create_taxonomy_update_state",)
    assert registry["user_report_samples"].call_type == REPORT_TEXT


def test_registry_excludes_legacy_false_friend_names() -> None:
    names = set(get_llm_function_registry())

    assert "llm_action_catalog" not in names
    assert "workflow_family_id" not in names
    assert "open_workflow" not in names
    assert "inspect_workflow" not in names
    assert "execute_workflow" not in names
