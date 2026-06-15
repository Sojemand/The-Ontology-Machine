from __future__ import annotations

from edit_suite.surfaces.operation_models import operation_preview_models
from edit_suite.surfaces.sections import build_sections
from edit_suite.surfaces.types import ModuleSurfaceBundle, SurfaceModel
from surfaces_support import entry


def test_preview_models_compact_taxonomy_release_draft_payloads() -> None:
    bundle = ModuleSurfaceBundle(
        source="contract",
        surfaces=(
            SurfaceModel(
                "normalizer.taxonomy_release_draft",
                "Taxonomy / Projection Release",
                "taxonomy_release_draft",
                True,
                "taxonomy_release_draft",
                {},
                {
                    "artifact_root": "C:/Artifact Tree",
                    "release": {"release_id": "rel.v1", "release_version": "2026.03", "projections": [{"projection_id": "invoice"}]},
                    "verification": {"status": "draft_loaded"},
                },
                {
                    "artifact_root": "C:/Artifact Tree",
                    "release": {
                        "release_id": "rel.v2",
                        "release_version": "2026.04",
                        "projections": [{"projection_id": "invoice"}, {"projection_id": "contract"}],
                    },
                    "verification": {"status": "verified"},
                },
                (),
            ),
        ),
    )

    sections = {section.name: section for section in build_sections(entry(), bundle, {})}
    preview_by_id = {surface.surface_id: surface for surface in sections["Preview/Drift"].surfaces}

    assert preview_by_id["normalizer.taxonomy_release_draft"].editor_kind == "preview_result"
    assert "current" not in preview_by_id["normalizer.taxonomy_release_draft"].value
    assert preview_by_id["normalizer.taxonomy_release_draft"].value["current_summary"]["projection_count"] == 1
    assert preview_by_id["normalizer.taxonomy_release_draft"].value["draft_summary"]["projection_count"] == 2
    assert preview_by_id["normalizer.taxonomy_release_draft"].value["draft_summary"]["verification_status"] == "verified"


def test_operation_preview_models_use_dedicated_review_editor_for_review_payloads() -> None:
    preview = operation_preview_models(
        {
            "normalizer.taxonomy_release_draft": {
                "label": "Review Data-Informed",
                "contract_module": "normalizer_vision.edit_contract",
                "response": {"status": "ok", "headline": "Data-informed review ready", "review_payload": {"review_mode": "data_informed"}},
            }
        }
    )

    assert len(preview) == 1
    assert preview[0].editor_kind == "review_result"
    assert preview[0].descriptor["preview"] == ["summary", "review"]


def test_operation_preview_models_use_preview_result_editor_for_non_review_payloads() -> None:
    preview = operation_preview_models(
        {
            "normalizer.taxonomy_release_draft": {
                "label": "Preview Impact",
                "contract_module": "normalizer_vision.edit_contract",
                "response": {
                    "status": "ok",
                    "headline": "Impact preview ready",
                    "changed_source_files": ["master.text.de.yaml"],
                    "current_release_fingerprint": "old",
                    "candidate_release_fingerprint": "new",
                    "release_fingerprint_changed": True,
                },
            }
        }
    )

    assert len(preview) == 1
    assert preview[0].editor_kind == "preview_result"
    assert preview[0].descriptor["preview"] == ["summary", "workflow_preview"]
