from __future__ import annotations

from pathlib import Path

from phase12_merge_entry_support import runtime_for, target_root
from phase12_merge_source_support import pending_request, seed_merge_source, submit_payload

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.services.agent_tool_workflow_dispatch import dispatch_permanent_workflow_tool
from semantic_control_kernel.surface.client_frontend_bridge import submit_user_interaction_response


def test_agent_facing_merge_collects_sources_and_target_through_ui_state(tmp_path: Path, monkeypatch) -> None:
    paths = StatePaths.from_state_root(tmp_path / "state")
    paths.ensure_layout()
    source_a = seed_merge_source(paths, tmp_path, "source_a", release_version="1.0.0")
    source_b = seed_merge_source(paths, tmp_path, "source_b", release_version="2.0.0")
    monkeypatch.setattr(
        "semantic_control_kernel.services.agent_tool_workflow_dispatch._merge_runtime",
        lambda _paths: runtime_for(tmp_path),
    )

    started = dispatch_permanent_workflow_tool("database_merge_additive_only", state_paths=paths).to_dict()

    assert started["status"] == "ok"
    assert started["effect"] == "workflow_started"
    first_request = pending_request(paths, started["workflow_run_id"])
    assert first_request["interaction_function"] == "choose_merge_database_count"

    after_count = submit_user_interaction_response(
        submit_payload(first_request, "irs_merge_count", text_value="2"),
        state_paths=paths,
        continue_inline=True,
    )

    assert after_count["continued_workflow_result"]["status"] == "ok"
    source_request = pending_request(paths, started["workflow_run_id"])
    assert source_request["interaction_function"] == "choose_databases_to_merge"
    assert source_request["prefilled_values"]["manual_path_count"] == 2
    assert str(source_a / "Corpus" / "corpus.db") in {option["database_path"] for option in source_request["options"]}

    after_sources = submit_user_interaction_response(
        submit_payload(source_request, "irs_merge_sources", selected_database_paths=[str(source_a), str(source_b)]),
        state_paths=paths,
        continue_inline=True,
    )

    assert after_sources["continued_workflow_result"]["status"] == "ok"
    target_request = pending_request(paths, started["workflow_run_id"])
    assert target_request["interaction_function"] == "choose_new_artifact_root_folder"

    after_target = submit_user_interaction_response(
        submit_payload(target_request, "irs_merge_target", path_value=str(target_root(tmp_path))),
        state_paths=paths,
        continue_inline=True,
    )

    assert after_target["continued_workflow_result"]["status"] == "ok"
    mode_request = pending_request(paths, started["workflow_run_id"])
    assert mode_request["interaction_function"] == "choose_merge_projection_mode"
    assert {option["choice_id"] for option in mode_request["options"]} == {
        "preserve_source_projections",
        "merge_to_single_projection",
    }

    finished = submit_user_interaction_response(
        submit_payload(mode_request, "irs_merge_projection_mode", choice_id="preserve_source_projections"),
        state_paths=paths,
        continue_inline=True,
    )

    result = finished["continued_workflow_result"]
    assert result["status"] == "ok"
    assert result["effect"] == "workflow_completed"
    assert result["final_state"] == "semantic_release_active"
    assert result["mirror_event"]["agent_explanation_guidance"]["response_mode"] == "explain_now"
    completion = result["mirror_event"]["technical_detail_ref"]["workflow_completion"]
    assert completion["source_database_count"] == 2
    assert {item["source_semantic_release_version"] for item in completion["source_databases"]} == {"1.0.0", "2.0.0"}
    assert (target_root(tmp_path) / "Corpus" / "corpus.db").exists()
