from __future__ import annotations

from pathlib import Path

import pytest

from normalizer_vision.source_authoring import kernel_component_materialization
from normalizer_vision.source_authoring.operations import dispatch

from tests.kernel_semantic_release_support import MODULE_ROOT, owner_request


def test_phase19_semantic_release_actions_are_registered_and_callable(tmp_path: Path) -> None:
    semantic_release_folder = tmp_path / "Semantic Release"
    taxonomy_update_state = {
        "schema_version": "kernel.create_taxonomy_update_state.input.v1",
        "taxonomy_id": "taxonomy_phase19",
        "taxonomy_core": {"codes": ["alpha", "beta"]},
        "runtime_locale": "en",
    }
    projection_update_state = {
        "schema_version": "kernel.create_projections_update_state.input.v1",
        "projection_ids": ["projection_phase19"],
        "projection_precursors": [{"projection_id": "projection_phase19"}],
        "semantic_binding": {"codes": ["alpha"]},
        "runtime_locale": "en",
    }

    staged_taxonomy = dispatch(
        "materialize_custom_taxonomy_artifact",
        owner_request(
            "materialize_custom_taxonomy_artifact",
            semantic_release_folder=str(semantic_release_folder),
            update_state_payload=taxonomy_update_state,
        ),
        project_root=MODULE_ROOT,
    )
    staged_projection = dispatch(
        "materialize_custom_projection_artifact",
        owner_request(
            "materialize_custom_projection_artifact",
            semantic_release_folder=str(semantic_release_folder),
            update_state_payload=projection_update_state,
            taxonomy_ref=staged_taxonomy["output_refs"]["component_identity"],
        ),
        project_root=MODULE_ROOT,
    )
    validated = dispatch(
        "validate_projection_binding",
        owner_request(
            "validate_projection_binding",
            taxonomy_ref=staged_taxonomy["output_refs"]["component_identity"],
            projection_refs=[staged_projection["output_refs"]["component_identity"]],
        ),
        project_root=MODULE_ROOT,
    )
    compiled = dispatch(
        "compile_semantic_release_candidate",
        owner_request(
            "compile_semantic_release_candidate",
            taxonomy_ref=staged_taxonomy["output_refs"]["component_identity"],
            projection_refs=[staged_projection["output_refs"]["component_identity"]],
            runtime_locale="en",
            semantic_release_folder=str(semantic_release_folder),
        ),
        project_root=MODULE_ROOT,
    )
    applied = dispatch(
        "apply_projection_update_state",
        owner_request(
            "apply_projection_update_state",
            base_release_ref=compiled["output_refs"]["release_ref"],
            taxonomy_ref=staged_taxonomy["output_refs"]["component_identity"],
            update_state=projection_update_state,
            operation_mode="additive",
        ),
        project_root=MODULE_ROOT,
    )
    merged = dispatch(
        "merge_semantic_release_candidates",
        owner_request(
            "merge_semantic_release_candidates",
            merge_run_id="merge_norm",
            source_release_refs=[compiled["output_refs"]["release_ref"], compiled["output_refs"]["release_ref"]],
        ),
        project_root=MODULE_ROOT,
    )

    assert staged_taxonomy["status"] == "ok"
    assert staged_projection["status"] == "ok"
    assert validated["output_refs"]["is_valid"] is True
    assert compiled["output_refs"]["release_ref"]["release_id"]
    assert applied["output_refs"]["work_package_ref"]["updated_release_ref"]["release_id"]
    assert merged["output_refs"]["semantic_merge_package"]["merge_run_id"] == "merge_norm"
    assert merged["output_refs"]["reconciled_taxonomy_ref"]["taxonomy_id"] == "taxonomy_phase19"
    assert merged["output_refs"]["reconciled_projection_refs"][0]["projection_id"] == "projection_phase19"
    assert merged["output_refs"]["semantic_merge_package"]["taxonomy_ref"]["taxonomy_id"] == "taxonomy_phase19"
    assert merged["output_refs"]["semantic_merge_package"]["projection_refs"][0]["projection_id"] == "projection_phase19"
    assert merged["output_refs"]["semantic_merge_fingerprint"]


def test_materialize_custom_projection_preserves_multi_projection_identity(tmp_path: Path) -> None:
    semantic_release_folder = tmp_path / "Semantic Release"
    taxonomy_ref = {
        "taxonomy_id": "taxonomy_multi",
        "taxonomy_fingerprint": "fp_taxonomy_multi",
        "runtime_locale": "en",
        "codes": ["finance", "invoice", "receipt", "issuer", "amount_due", "other"],
    }
    projection_update_state = {
        "schema_version": "kernel.create_projections_update_state.input.v1",
        "projection_precursors": [
            {
                "projection_id": "finance.receipts.v1",
                "domain_ids": ["finance"],
                "include_document_types": ["receipt", "other"],
                "include_field_codes": ["issuer", "amount_due", "other"],
            },
            {
                "projection_id": "finance.invoices.v1",
                "domain_ids": ["finance"],
                "include_document_types": ["invoice", "other"],
                "include_field_codes": ["issuer", "amount_due", "other"],
            },
        ],
        "runtime_locale": "en",
    }

    staged_projection = dispatch(
        "materialize_custom_projection_artifact",
        owner_request(
            "materialize_custom_projection_artifact",
            semantic_release_folder=str(semantic_release_folder),
            update_state_payload=projection_update_state,
            taxonomy_ref=taxonomy_ref,
        ),
        project_root=MODULE_ROOT,
    )
    output = staged_projection["output_refs"]
    projection_refs = output["projection_refs"]
    compiled = dispatch(
        "compile_semantic_release_candidate",
        owner_request(
            "compile_semantic_release_candidate",
            taxonomy_ref=taxonomy_ref,
            staged_projection_ref={"component_identity": output["component_identity"]},
            runtime_locale="en",
            semantic_release_folder=str(semantic_release_folder),
        ),
        project_root=MODULE_ROOT,
    )

    assert output["projection_ids"] == ["finance.receipts.v1", "finance.invoices.v1"]
    assert [item["projection_id"] for item in projection_refs] == output["projection_ids"]
    assert output["component_identity"]["projection_refs"] == projection_refs
    assert output["component_identity"]["projection_set_fingerprint"] == output["projection_set_fingerprint"]
    assert compiled["output_refs"]["release_ref"]["projection_refs"] == projection_refs


def test_kernel_component_writer_uses_atomic_text_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_atomic_text_write(path: Path, text: str) -> None:
        captured["path"] = path
        captured["text"] = text

    monkeypatch.setattr(kernel_component_materialization, "atomic_text_write", fake_atomic_text_write)

    written = kernel_component_materialization.write_component(tmp_path / "taxonomy.json", {"z": 1, "a": 2})

    assert written == str(tmp_path / "taxonomy.json")
    assert captured["path"] == tmp_path / "taxonomy.json"
    assert str(captured["text"]).endswith("\n")
    assert str(captured["text"]).index('"a"') < str(captured["text"]).index('"z"')


def test_phase19_semantic_release_actions_reject_missing_request_fingerprint(tmp_path: Path) -> None:
    semantic_release_folder = tmp_path / "Semantic Release"
    payload = owner_request(
        "materialize_custom_taxonomy_artifact",
        semantic_release_folder=str(semantic_release_folder),
        update_state_payload={
            "schema_version": "kernel.create_taxonomy_update_state.input.v1",
            "taxonomy_id": "taxonomy_phase19",
            "taxonomy_core": {"codes": ["alpha"]},
        },
    )
    payload.pop("request_fingerprint")

    with pytest.raises(ValueError, match="request_fingerprint"):
        dispatch("materialize_custom_taxonomy_artifact", payload, project_root=MODULE_ROOT)  # type: ignore[arg-type]
