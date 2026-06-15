from __future__ import annotations

import json
from pathlib import Path

from phase19_adapter_unblock_support import (
    AdapterCallResult,
    PIPELINE_ROOT,
    SemanticReleaseAdapter,
    _custom_taxonomy_ref,
    _story_projection_precursor,
)

def test_create_custom_projection_uses_precursor_identity_without_phase19_fallback(tmp_path: Path) -> None:
    semantic = SemanticReleaseAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    result = semantic.create_custom_projection(
        {
            "update_state": {
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [
                    {
                        "projection_id": "finance.receipts.v1",
                        "domain_ids": ["finance"],
                        "include_document_types": ["invoice", "other"],
                        "include_field_codes": ["amount_due", "other"],
                    }
                ],
            },
            "taxonomy_ref": {"allowed_codes": ["finance", "invoice", "amount_due", "other"]},
            "target_identity": {},
        }
    )

    output = result.to_dict()["output_refs"]
    assert output["projection_ids"] == ["finance.receipts.v1"]
    assert output["component_identity"]["projection_id"] == "finance.receipts.v1"
    assert "amount_due" in output["component_identity"]["included_taxonomy_codes"]
    assert "projection_phase19" not in json.dumps(output)

def test_write_custom_release_accepts_full_custom_taxonomy_without_base_release(tmp_path: Path) -> None:
    semantic = SemanticReleaseAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    semantic_release_path = tmp_path / "Artifact Tree" / "Semantic Release"
    release_path = semantic_release_path / "releases" / "custom.story.release"

    result = semantic.write_semantic_release(
        {
            "release_path": str(release_path),
            "semantic_release_path": str(semantic_release_path),
            "release_ref": {
                "release_id": "custom.story.release",
                "release_version": "custom.v1",
                "release_fingerprint": "candidate-fingerprint",
                "taxonomy_ref": _custom_taxonomy_ref(),
                "projection_refs": [
                    {
                        "projection_id": "creative_writing.short_story_text.v1",
                        "projection_fingerprint": "proj-story-fp",
                        "included_taxonomy_codes": ["short_story", "story_title", "story_paragraph", "narration_text", "other"],
                    }
                ],
                "runtime_locale": "en",
            },
            "projection_update_state": {
                "schema_version": "kernel.create_projections_update_state.input.v1",
                "projection_precursors": [_story_projection_precursor()],
            },
            "target_identity": {},
        }
    )

    output = result.to_dict()["output_refs"]
    written = json.loads(Path(output["release_path"]).read_text(encoding="utf-8"))
    assert result.status == "ok"
    assert written["release_id"] == "custom.story.release"
    assert written["release_fingerprint"] == written["fingerprint"]
    assert written["master_taxonomy_id"] == "custom.story.taxonomy"
    assert written["projection_ids"] == ["creative_writing.short_story_text.v1"]

def test_write_merge_custom_release_uses_detached_materialization_without_update_state(tmp_path: Path) -> None:
    semantic = SemanticReleaseAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    captured: list[dict[str, object]] = []

    def capture_invoke(**kwargs):
        captured.append(dict(kwargs))
        return AdapterCallResult(
            {
                "adapter_call_id": "adc_capture",
                "adapter_name": "SemanticReleaseAdapter",
                "capability_status": kwargs["capability_status"],
                "diagnostics": [],
                "kernel_function": kwargs["kernel_function"],
                "output_refs": {"release_path": kwargs["request_payload"].get("output_path")},
                "receipt_fields": {},
                "schema_version": "adapter.call_result.v1",
                "status": "ok",
                "target_identity_proof": {"release_fingerprint": "sha256:merged"},
            }
        )

    semantic.invoke = capture_invoke
    semantic_release_path = tmp_path / "Artifact Tree" / "Semantic Release"

    result = semantic.write_semantic_release(
        {
            "merge_context": {"merge_run_id": "mrg_test"},
            "release_path": str(semantic_release_path / "releases" / "merged.release"),
            "release_ref": {
                "release_id": "merged.release",
                "release_version": "custom.v1",
                "release_fingerprint": "sha256:merged",
                "runtime_locale": "en",
                "taxonomy_ref": _custom_taxonomy_ref(),
                "projection_refs": [
                    {
                        "projection_id": "creative_writing.short_story_text.v1",
                        "projection_fingerprint": "proj-story-fp",
                    }
                ],
            },
            "semantic_merge_package": {"release_id": "merged.release"},
            "semantic_release_path": str(semantic_release_path),
            "target_identity": {},
        }
    )

    assert result.status == "ok"
    assert captured[0]["owner_action"] == "materialize_semantic_release_candidate"
    assert captured[0]["owner_contract_module"] == "normalizer_vision.edit_contract"
    assert "release_ref" in captured[0]["request_payload"]

def test_semantic_release_adapter_keeps_kernel_attach_target_local_by_default(tmp_path: Path) -> None:
    semantic = SemanticReleaseAdapter(**{"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT})
    captured_payloads: list[dict[str, object]] = []

    def capture_invoke(**kwargs):
        captured_payloads.append(dict(kwargs["request_payload"]))
        return AdapterCallResult(
            {
                "adapter_call_id": "capture",
                "adapter_name": "semantic_release",
                "capability_status": "implemented_in_pipeline",
                "diagnostics": [],
                "kernel_function": kwargs["kernel_function"],
                "output_refs": {},
                "receipt_fields": {},
                "status": "ok",
                "target_identity_proof": {},
            }
        )

    semantic.invoke = capture_invoke

    semantic.load_semantic_release({"release_path": "release", "corpus_db_path": "db"})
    semantic.preflight_semantic_release_activation({"release_path": "release", "corpus_db_path": "db"})
    semantic.activate_semantic_release({"release_path": "release", "corpus_db_path": "db"})
    semantic.load_semantic_release({"release_path": "release", "corpus_db_path": "db", "write_global_mirrors": True})

    assert captured_payloads[0]["write_global_mirrors"] is False
    assert captured_payloads[2]["write_global_mirrors"] is False
    assert captured_payloads[3]["write_global_mirrors"] is True
    assert all(str(payload["release_path"]).endswith("release.json") for payload in captured_payloads)
