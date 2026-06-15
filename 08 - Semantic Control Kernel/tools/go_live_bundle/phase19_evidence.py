from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import _mkdir, _write_json


def _write_phase19_evidence(bundle_root: Path, run_id: str, command_records: list[dict[str, Any]]) -> Path:
    snapshots_dir = bundle_root / "snapshots" / "phase19_receipts"
    _mkdir(snapshots_dir)
    capabilities = [
        _phase19_capability(
            snapshots_dir,
            "artifact_tree_contract_hardening",
            "00 - Orchestrator",
            ["create_artifact_tree", "validate_artifact_tree"],
            ["00 - Orchestrator/module-manifest.json"],
            ["00 - Orchestrator/README.md"],
            [r'dev-tests\run-tests.bat tests\test_kernel_artifact_tree_contract.py tests\test_kernel_batch_manifest_contract.py'],
            ["commands/31_orchestrator_owner_contracts.log"],
            ["commands/22_kernel_phase19.log"],
            "create_and_validate_artifact_tree",
            command_records,
            {"kernel:phase19", "orchestrator:owner_contracts"},
        ),
        _phase19_capability(
            snapshots_dir,
            "semantic_release_domain_service",
            "04 - Normalizer",
            [
                "materialize_custom_taxonomy_artifact",
                "materialize_custom_projection_artifact",
                "validate_projection_binding",
                "compile_semantic_release_candidate",
                "merge_semantic_release_candidates",
            ],
            ["04 - Normalizer/normalizer_vision/edit_contract/workflow.py"],
            ["04 - Normalizer/README.md"],
            [r'dev-tests\run-tests.bat tests\test_kernel_semantic_release_domain_service.py'],
            ["commands/32_normalizer_owner_contracts.log"],
            ["commands/22_kernel_phase19.log"],
            "semantic_release_materialization",
            command_records,
            {"kernel:phase19", "normalizer:owner_contracts"},
        ),
        _phase19_capability(
            snapshots_dir,
            "pipeline_batch_manifest_service",
            "00 - Orchestrator",
            [
                "create_pipeline_batch_manifest",
                "finalize_pipeline_batch_manifest",
            ],
            ["00 - Orchestrator/module-manifest.json"],
            ["00 - Orchestrator/README.md"],
            [r'dev-tests\run-tests.bat tests\test_kernel_batch_manifest_contract.py'],
            ["commands/31_orchestrator_owner_contracts.log"],
            ["commands/22_kernel_phase19.log"],
            "pipeline_batch_manifest",
            command_records,
            {"kernel:phase19", "orchestrator:owner_contracts"},
        ),
        _phase19_capability(
            snapshots_dir,
            "multi_source_merge_domain_service",
            "05 - Corpus Builder + 04 - Normalizer",
            [
                "multi_source_merge_preflight",
                "multi_source_merge_databases",
                "write_merge_reconciliation_manifest",
                "backfill_sql_from_merge_artifacts",
                "merge_semantic_release_candidates",
            ],
            ["05 - Corpus Builder/module-manifest.json", "04 - Normalizer/normalizer_vision/edit_contract/workflow.py"],
            ["05 - Corpus Builder/README.md", "04 - Normalizer/README.md"],
            [r'dev-tests\run-tests.bat tests\test_kernel_multi_source_merge_domain_service.py'],
            ["commands/33_corpus_owner_contracts.log", "commands/32_normalizer_owner_contracts.log"],
            ["commands/22_kernel_phase19.log"],
            "multi_source_merge_execution",
            command_records,
            {"kernel:phase19", "corpus:owner_contracts", "normalizer:owner_contracts"},
        ),
    ]
    related_commands = {
        "kernel:phase19",
        "orchestrator:owner_contracts",
        "normalizer:owner_contracts",
        "corpus:owner_contracts",
    }
    live_phase19_complete = command_records != [] and all(
        record["result"] == "pass"
        for record in command_records
        if f"{record['module_key']}:{record['purpose']}" in related_commands
    )
    payload = {
        "schema_version": "semantic_control_kernel.phase20.phase19_owner_capability_evidence.v1",
        "go_live_run_id": run_id,
        "evidence_status": "owner_tested_live_matrix_executed" if live_phase19_complete else "owner_tested_live_command_execution_pending",
        "blocking_reason": (
            "Phase 19 owner and adapter commands passed inside the live go-live matrix."
            if live_phase19_complete
            else "Owner-module and adapter evidence refs are present, but the live Phase 19 command slice did not fully pass."
        ),
        "capabilities": capabilities,
    }
    path = bundle_root / "phase19_owner_capability_evidence.json"
    _write_json(path, payload)
    return path


def _phase19_capability(
    snapshots_dir: Path,
    capability_name: str,
    owner_module: str,
    owner_action_names: list[str],
    owner_manifest_paths: list[str],
    owner_readme_paths: list[str],
    owner_test_commands: list[str],
    owner_test_log_refs: list[str],
    adapter_test_log_refs: list[str],
    receipt_name: str,
    command_records: list[dict[str, Any]],
    required_command_keys: set[str],
) -> dict[str, Any]:
    related_records = [
        record
        for record in command_records
        if f"{record['module_key']}:{record['purpose']}" in required_command_keys
    ]
    live_verified = bool(related_records) and all(record["result"] == "pass" for record in related_records)
    receipt = {
        "schema_version": "semantic_control_kernel.phase20.capability_receipt_sample.v1",
        "owner_module": owner_module,
        "owner_action": owner_action_names[0],
        "capability": capability_name,
        "workflow_run_id": f"wr_{receipt_name}",
        "adapter_call_id": f"adc_{receipt_name}",
        "target_identity": {"target_hash": f"target_{receipt_name}"},
        "artifact_refs": [{"ref": f"artifacts/{receipt_name}.json"}],
        "diagnostics": [
            {
                "code": "owner_tested_live_matrix" if live_verified else "live_command_execution_pending",
                "log_refs": [record["log_path"] for record in related_records],
            }
        ],
        "receipt_origin": "phase20_bundle_contract_sample",
        "result_status": "ok" if live_verified else "unverified",
    }
    receipt_path = snapshots_dir / f"{receipt_name}.json"
    _write_json(receipt_path, receipt)
    return {
        "capability_name": capability_name,
        "owner_module": owner_module,
        "owner_action_names": owner_action_names,
        "owner_manifest_paths": owner_manifest_paths,
        "owner_readme_paths": owner_readme_paths,
        "owner_test_commands": owner_test_commands,
        "owner_test_log_refs": owner_test_log_refs,
        "adapter_test_log_refs": adapter_test_log_refs,
        "capability_receipt_sample_refs": [receipt_path.relative_to(bundle_root_from_snapshots(snapshots_dir)).as_posix()],
        "missing_capability_happy_path_result": "none_returned" if live_verified else "verification_pending",
        "supported_happy_paths_covered": owner_action_names,
        "unsupported_paths_still_blocked": ["real unsupported conditions remain typed blockers; supported happy paths must not return former missing-capability blockers."],
        "live_verification_status": "verified_by_live_matrix" if live_verified else "pending_or_failed_live_matrix",
        "live_verification_command_keys": sorted(required_command_keys),
    }


def bundle_root_from_snapshots(snapshots_dir: Path) -> Path:
    return snapshots_dir.parents[1]
