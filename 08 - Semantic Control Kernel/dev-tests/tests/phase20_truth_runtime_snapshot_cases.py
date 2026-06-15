from __future__ import annotations

from pathlib import Path

from phase20_go_live_support import load_json
from phase20_truth_support import module
from semantic_control_kernel.repository.paths import StatePaths


def test_client_frontend_snapshot_is_runtime_sourced_from_live_bridge_contract(tmp_path: Path) -> None:
    state_paths = StatePaths.from_state_root(tmp_path / "state")
    module._write_client_frontend_snapshot(tmp_path, "glv_unit", state_paths=state_paths)

    payload = load_json(tmp_path / "client_frontend_event_snapshot.json")
    kinds = {event["frontend_event_kind"] for event in payload["events"]}
    mirror_events = [
        event["mirror_event"]
        for event in payload["events"]
        if event["frontend_event_kind"] == "mirror_event"
    ]

    assert payload["source_contract"] == "kernel_list_client_frontend_events"
    assert payload["runtime_state_root"] == "08 - Semantic Control Kernel/state"
    assert {"interaction_request", "progress_event", "mirror_event", "tool_availability"} <= kinds
    assert payload["source_event_refs"]["interaction_request_refs"]
    assert payload["source_event_refs"]["progress_event_refs"]
    assert payload["source_event_refs"]["mirror_event_refs"]
    assert payload["source_event_refs"]["tool_availability_refs"]
    assert any(
        mirror["event_type"] == "llm_validation_failed_final"
        and str(mirror["support_bundle_ref"]["support_bundle_path"]).startswith("support/bundles/")
        for mirror in mirror_events
    )


def test_client_frontend_snapshot_can_be_regenerated_for_the_same_run_id(tmp_path: Path) -> None:
    state_paths = StatePaths.from_state_root(tmp_path / "state")

    module._write_client_frontend_snapshot(tmp_path, "glv_unit", state_paths=state_paths)
    module._write_client_frontend_snapshot(tmp_path, "glv_unit", state_paths=state_paths)

    payload = load_json(tmp_path / "client_frontend_event_snapshot.json")

    assert payload["source_contract"] == "kernel_list_client_frontend_events"
    assert any(event["frontend_event_kind"] == "mirror_event" for event in payload["events"])


def test_support_bundle_sample_is_derived_from_runtime_bundle_path(tmp_path: Path) -> None:
    state_paths = StatePaths.from_state_root(tmp_path / "state")
    module._write_support_bundle_sample(tmp_path, "glv_unit", state_paths=state_paths)

    payload = load_json(tmp_path / "support_bundle_sample_manifest.json")
    runtime_support_ref = payload["runtime_support_bundle_ref"]
    runtime_refs = payload["runtime_bundle_file_refs"]

    assert payload["source_contract"] == "semantic_control_kernel.repository.support_bundles.SupportBundleStore"
    assert runtime_support_ref["support_bundle_path"] == runtime_refs["manifest_ref"]
    assert runtime_support_ref["support_bundle_path"].startswith("support/bundles/")
    assert runtime_refs["safe_summary_ref"].startswith("support/bundles/")
    assert runtime_refs["included_refs_ref"].startswith("support/bundles/")
    assert runtime_refs["redaction_report_ref"].startswith("support/bundles/")
    assert runtime_refs["trace_links_ref"].startswith("support/bundles/")
    assert str(payload["runtime_persisted_redaction_report_ref"]).startswith("debug/redaction_reports/")
    assert (tmp_path / payload["safe_summary_path"]).is_file()
    assert (tmp_path / payload["included_refs_path"]).is_file()
    assert (tmp_path / payload["redaction_report_path"]).is_file()
    assert (tmp_path / payload["trace_links_path"]).is_file()
    assert (tmp_path / payload["persisted_redaction_report_path"]).is_file()
    assert payload["source_file_hashes"]["safe_summary"]
    assert payload["source_file_hashes"]["persisted_redaction_report"]
