from __future__ import annotations

from pathlib import Path

from phase20_go_live_support import command_matrix, latest_go_live_dir, load_json


PHASE19_COMMAND_KEYS = {
    "kernel:phase19",
    "orchestrator:owner_contracts",
    "normalizer:owner_contracts",
    "corpus:owner_contracts",
}


def test_phase19_owner_capability_evidence_records_real_blocker_state() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "phase19_owner_capability_evidence.json")
    manifest = load_json(root / "go_live_manifest.json")
    records = command_matrix()["commands"]
    live_complete = all(
        record["result"] == "pass"
        for record in records
        if f"{record['module_key']}:{record['purpose']}" in PHASE19_COMMAND_KEYS
    )

    assert payload["schema_version"] == "semantic_control_kernel.phase20.phase19_owner_capability_evidence.v1"
    assert payload["evidence_status"] == (
        "owner_tested_live_matrix_executed" if live_complete else "owner_tested_live_command_execution_pending"
    )
    assert manifest["decision"] in {"ready", "ready_with_exceptions", "not_ready"}
    assert len(payload["capabilities"]) == 4


def test_phase19_capability_entries_have_required_refs_and_receipt_samples() -> None:
    root = latest_go_live_dir()
    payload = load_json(root / "phase19_owner_capability_evidence.json")

    for capability in payload["capabilities"]:
        receipt_refs = capability["capability_receipt_sample_refs"]
        for field_name in (
            "capability_name",
            "owner_module",
            "owner_action_names",
            "owner_manifest_paths",
            "owner_readme_paths",
            "owner_test_commands",
            "owner_test_log_refs",
            "adapter_test_log_refs",
            "capability_receipt_sample_refs",
            "missing_capability_happy_path_result",
            "supported_happy_paths_covered",
            "unsupported_paths_still_blocked",
            "live_verification_status",
            "live_verification_command_keys",
        ):
            assert capability[field_name]
        related_keys = set(capability["live_verification_command_keys"])
        live_verified = all(
            record["result"] == "pass"
            for record in command_matrix()["commands"]
            if f"{record['module_key']}:{record['purpose']}" in related_keys
        )
        assert capability["missing_capability_happy_path_result"] == (
            "none_returned" if live_verified else "verification_pending"
        )
        assert capability["live_verification_status"] == (
            "verified_by_live_matrix" if live_verified else "pending_or_failed_live_matrix"
        )
        for relative in receipt_refs:
            assert (root / relative).is_file()
            receipt = load_json(root / relative)
            assert receipt["receipt_origin"] == "phase20_bundle_contract_sample"
            assert receipt["result_status"] == ("ok" if live_verified else "unverified")
