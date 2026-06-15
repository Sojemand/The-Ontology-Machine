from __future__ import annotations

from pathlib import Path

from semantic_control_kernel.adapters.invocation import AdapterInvocation
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.types.adapter_results import AdapterCallResult


def test_default_release_export_reports_export_kernel_function(monkeypatch, tmp_path: Path) -> None:
    captured: list[AdapterInvocation] = []

    def fake_invoke(invocation: AdapterInvocation) -> AdapterCallResult:
        captured.append(invocation)
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_default_export",
                "adapter_name": invocation.boundary.adapter_name,
                "capability_status": invocation.boundary.capability_status,
                "diagnostics": [],
                "kernel_function": invocation.kernel_function,
                "output_refs": {
                    "output_path": str(tmp_path / "Artifact Tree" / "Semantic Release" / "default_semantic_release.export.json"),
                    "release_ref": {
                        "release_id": "default.release.v1",
                        "release_version": "1.0.0",
                        "release_fingerprint": "fp_default",
                        "taxonomy_ref": {
                            "taxonomy_id": "default.taxonomy.v1",
                            "taxonomy_fingerprint": "fp_taxonomy",
                        },
                        "projection_refs": [
                            {
                                "projection_id": "default.projection.v1",
                                "projection_fingerprint": "fp_projection",
                            }
                        ],
                    },
                },
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {"release_fingerprint": "fp_default"},
            }
        )

    monkeypatch.setattr("semantic_control_kernel.adapters.base.invoke_owner_contract", fake_invoke)

    result = SemanticReleaseAdapter(state_root=tmp_path / "state").export_default_semantic_release(
        {
            "blueprint_ref": "default-blueprint",
            "semantic_release_path": str(tmp_path / "Artifact Tree" / "Semantic Release"),
            "target_identity": {},
        }
    )

    assert result.to_dict()["kernel_function"] == "export_default_semantic_release"
    assert captured[0].kernel_function == "export_default_semantic_release"
    assert captured[0].boundary.owner_action == "export_default_blueprint_release"
    assert captured[0].request_payload["action"] == "export_default_blueprint_release"
    assert captured[0].request_payload["blueprint_ref"] == "default"
    assert captured[0].request_payload["output_path"].endswith("default_semantic_release.export.json")


def test_merge_mutations_require_source_database_ids_and_hashed_target_proof(monkeypatch, tmp_path: Path) -> None:
    captured: list[AdapterInvocation] = []

    def fake_invoke(invocation: AdapterInvocation) -> AdapterCallResult:
        captured.append(invocation)
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_merge_test",
                "adapter_name": invocation.boundary.adapter_name,
                "capability_status": invocation.boundary.capability_status,
                "diagnostics": [],
                "kernel_function": invocation.kernel_function,
                "output_refs": {},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    monkeypatch.setattr("semantic_control_kernel.adapters.base.invoke_owner_contract", fake_invoke)

    database_path = tmp_path / "target.db"
    selection = {
        "merge_run_id": "merge_phase4",
        "target_database_path": str(database_path),
        "source_databases": [
            {"source_database_id": "db_a", "source_database_path": str(tmp_path / "a.db")},
            {"source_database_id": "db_b", "source_database_path": str(tmp_path / "b.db")},
        ],
    }

    MergeAdapter(state_root=tmp_path / "state").merge_empty_databases({"selection": selection})
    MergeAdapter(state_root=tmp_path / "state").write_merge_reconciliation_manifest(
        {
            "merge_run_id": "merge_phase4",
            "collision_manifest": {
                "manifest_fingerprint": "sha256:manifest",
                "target_database_path": str(database_path),
            },
            "selected_resolutions": [],
        }
    )

    assert captured[0].boundary.required_target_proof_fields == (
        "merge_run_id",
        "source_database_ids",
        "target_database_path_hash",
    )
    assert captured[0].target_identity["merge_run_id"] == "merge_phase4"
    assert captured[0].target_identity["source_database_ids"] == ["db_a", "db_b"]
    assert captured[0].target_identity["target_database_path_hash"].startswith("sha256:")
    assert captured[1].boundary.required_target_proof_fields == ("merge_run_id", "target_database_path_hash")
    assert "source_database_ids" not in captured[1].boundary.required_target_proof_fields
    assert captured[1].target_identity["target_database_path_hash"].startswith("sha256:")
    assert captured[1].request_payload["target_identity"]["target_database_path_hash"].startswith("sha256:")
    assert "reconciliation_receipt" not in captured[1].request_payload
