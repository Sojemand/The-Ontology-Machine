from __future__ import annotations

import json
from pathlib import Path

from normalizer_vision.semantic_release.kernel_merge import merge_candidates
from normalizer_vision.source_authoring.operations import dispatch
from normalizer_vision.taxonomy import upgrade_projection_payload_v2

from tests.kernel_semantic_release_support import MODULE_ROOT, owner_request, sectioned_taxonomy_update_state


def test_merge_candidates_additively_reconciles_taxonomy_and_projection_refs() -> None:
    merged = merge_candidates(
        merge_run_id="merge_additive",
        source_release_refs=[
            {
                "projection_refs": [
                    {
                        "projection_fingerprint": "sha256:projection_a",
                        "projection_id": "projection.a",
                        "projection_payload": {
                            "promotion_rules": [{"slot": "issuer", "source_paths": ["content.fields.issuer"]}],
                        },
                    }
                ],
                "taxonomy_ref": {
                    "master_taxonomy": {
                        "field_codes": [{"code": "issuer"}, {"code": "other"}],
                        "promotion_slots": [{"slot": "issuer", "label": "Issuer"}],
                        "taxonomy_id": "taxonomy.a",
                        "taxonomy_version": "v1",
                    },
                    "taxonomy_fingerprint": "sha256:taxonomy_a",
                    "taxonomy_id": "taxonomy.a",
                    "taxonomy_version": "v1",
                },
            },
            {
                "projection_refs": [
                    {
                        "projection_fingerprint": "sha256:projection_b",
                        "projection_id": "projection.b",
                        "projection_payload": {
                            "promotion_rules": [{"slot": "amount_due", "source_paths": ["content.fields.amount_due"]}],
                        },
                    }
                ],
                "taxonomy_ref": {
                    "master_taxonomy": {
                        "field_codes": [{"code": "amount_due"}, {"code": "other"}],
                        "promotion_slots": [{"slot": "amount_due", "label": "Amount Due"}],
                        "taxonomy_id": "taxonomy.b",
                        "taxonomy_version": "v1",
                    },
                    "taxonomy_fingerprint": "sha256:taxonomy_b",
                    "taxonomy_id": "taxonomy.b",
                    "taxonomy_version": "v1",
                },
            },
        ],
    )

    field_codes = {item["code"] for item in merged["reconciled_taxonomy_ref"]["master_taxonomy"]["field_codes"]}
    assert {"issuer", "amount_due", "other"} <= field_codes
    promotion_slots = {item["slot"] for item in merged["reconciled_taxonomy_ref"]["master_taxonomy"]["promotion_slots"]}
    assert {"issuer", "amount_due"} <= promotion_slots
    projection_rule_slots = {
        rule["slot"]
        for projection in merged["reconciled_projection_refs"]
        for rule in projection["projection_payload"]["promotion_rules"]
    }
    assert projection_rule_slots <= promotion_slots
    assert [item["projection_id"] for item in merged["reconciled_projection_refs"]] == ["projection.a", "projection.b"]
    assert merged["semantic_merge_package"]["taxonomy_ref"] == merged["reconciled_taxonomy_ref"]
    assert merged["semantic_merge_package"]["projection_refs"] == merged["reconciled_projection_refs"]


def test_merge_candidates_can_compile_source_projections_into_one_projection() -> None:
    merged = merge_candidates(
        merge_run_id="merge_single_projection",
        projection_merge_mode="merge_to_single_projection",
        source_release_refs=[
            _science_release(
                projection_id="projection.a",
                document_type="paper",
                field_code="hypothesis",
                row_type="experiment",
                cell_code="measurement",
                marker="method",
            ),
            _science_release(
                projection_id="projection.b",
                document_type="lab_note",
                field_code="result",
                row_type="observation",
                cell_code="value",
                marker="result",
            ),
        ],
    )

    projection_refs = merged["reconciled_projection_refs"]
    assert len(projection_refs) == 1
    projection = projection_refs[0]["projection_payload"]
    assert projection_refs[0]["projection_id"].startswith("merged.projection.")
    assert set(projection["include_document_types"]) == {"lab_note", "paper"}
    assert set(projection["include_field_codes"]) == {"hypothesis", "result"}
    assert set(projection["include_row_types"]) == {"experiment", "observation"}
    assert set(projection["include_cell_codes"]) == {"measurement", "value"}
    promotion_slots = {item["slot"] for item in merged["reconciled_taxonomy_ref"]["master_taxonomy"]["promotion_slots"]}
    assert promotion_slots == {"hypothesis", "result"}
    assert {rule["slot"] for rule in projection["promotion_rules"]} <= promotion_slots
    assert projection["compatibility"]["source_projection_ids"] == ["projection.a", "projection.b"]
    assert projection["label"] != "Merged Projection"
    assert "Science" in projection["label"]
    assert "Lab Note" in projection["label"] or "Paper" in projection["label"]
    assert projection["description"] != "Merged projection compiled from selected source projections."
    assert "Science" in projection["description"]
    assert "Hypothesis" in projection["description"] or "Result" in projection["description"]
    assert projection["routing"]["when_to_use"] != "Use when content matches any selected source projection."
    assert "Science" in projection["routing"]["when_to_use"]
    assert projection["routing"]["avoid_when"] != "Do not use when none of the selected source projection signals match."
    assert merged["semantic_merge_package"]["projection_merge_mode"] == "merge_to_single_projection"


def test_single_projection_merge_collapses_duplicate_promotion_slots() -> None:
    merged = merge_candidates(
        merge_run_id="merge_duplicate_slots",
        projection_merge_mode="merge_to_single_projection",
        source_release_refs=[
            _email_release(
                projection_id="projection.message",
                field_code="message_subject",
                source_path="content.fields.message_subject",
            ),
            _email_release(
                projection_id="projection.email",
                field_code="email_subject",
                source_path="content.fields.email_subject",
            ),
        ],
    )

    projection = merged["reconciled_projection_refs"][0]["projection_payload"]
    subject_rules = [rule for rule in projection["promotion_rules"] if rule["slot"] == "document_subject"]
    assert subject_rules == [
        {
            "slot": "document_subject",
            "source_paths": ["content.fields.message_subject", "content.fields.email_subject"],
        }
    ]
    assert len({rule["slot"] for rule in projection["promotion_rules"]}) == len(projection["promotion_rules"])

    upgrade_projection_payload_v2(
        merged["reconciled_taxonomy_ref"]["master_taxonomy"],
        projection,
    )


def test_single_projection_merge_does_not_truncate_description() -> None:
    merged = merge_candidates(
        merge_run_id="merge_long_description",
        projection_merge_mode="merge_to_single_projection",
        source_release_refs=[
            _verbose_release("projection.long.a", "Long Form Reflective Chapter Page"),
            _verbose_release("projection.long.b", "Comparative Philosophical Table Of Contents Page"),
        ],
    )

    description = merged["reconciled_projection_refs"][0]["projection_payload"]["description"]

    assert len(description) > 480
    assert not description.endswith("...")
    assert "Extensive Comparative Interpretive Passage Marker" in description


def test_materialize_custom_taxonomy_preserves_sectioned_update_state_and_identity_codes(tmp_path: Path) -> None:
    semantic_release_folder = tmp_path / "Semantic Release"
    taxonomy_update_state = sectioned_taxonomy_update_state()

    staged_taxonomy = dispatch(
        "materialize_custom_taxonomy_artifact",
        owner_request(
            "materialize_custom_taxonomy_artifact",
            semantic_release_folder=str(semantic_release_folder),
            update_state_payload=taxonomy_update_state,
        ),
        project_root=MODULE_ROOT,
    )
    artifact_path = semantic_release_folder / staged_taxonomy["output_refs"]["artifact_ref"]["artifact_path"]
    materialized = json.loads(artifact_path.read_text(encoding="utf-8"))
    identity_codes = set(materialized["identity"]["codes"])

    assert materialized["update_state"] == taxonomy_update_state
    assert {"finance", "invoice", "amount_due", "line_item", "description", "other"}.issubset(identity_codes)
    assert materialized["identity"] == staged_taxonomy["output_refs"]["component_identity"]


def _science_release(
    *,
    projection_id: str,
    document_type: str,
    field_code: str,
    row_type: str,
    cell_code: str,
    marker: str,
) -> dict:
    return {
        "projection_refs": [
            {
                "projection_fingerprint": f"sha256:{projection_id}",
                "projection_id": projection_id,
                "projection_payload": {
                    "domain_ids": ["science"],
                    "label": f"{document_type.title()} Science Projection",
                    "description": f"Projection for {document_type} science material.",
                    "include_document_types": [document_type],
                    "include_field_codes": [field_code],
                    "include_row_types": [row_type],
                    "include_cell_codes": [cell_code],
                    "promotion_rules": [{"slot": field_code, "source_field": field_code}],
                    "routing": {"example_document_types": [document_type], "surface_signals": {"text_markers": [marker]}},
                },
            }
        ],
        "taxonomy_ref": {
            "master_taxonomy": {
                "cell_codes": [{"code": cell_code, "label": cell_code.title()}],
                "document_types": [{"code": document_type, "label": document_type.title()}],
                "domains": [{"code": "science", "label": "Science"}],
                "field_codes": [{"code": field_code, "label": field_code.title()}],
                "promotion_slots": [{"slot": field_code, "label": field_code.title()}],
                "row_types": [{"code": row_type, "label": row_type.title()}],
                "taxonomy_id": f"taxonomy.{projection_id}",
                "taxonomy_version": "v1",
            },
            "taxonomy_fingerprint": f"sha256:taxonomy_{projection_id}",
            "taxonomy_id": f"taxonomy.{projection_id}",
            "taxonomy_version": "v1",
        },
    }


def _email_release(*, projection_id: str, field_code: str, source_path: str) -> dict:
    return {
        "projection_refs": [
            {
                "projection_fingerprint": f"sha256:{projection_id}",
                "projection_id": projection_id,
                "projection_payload": {
                    "domain_ids": ["email"],
                    "include_document_types": ["business_email"],
                    "include_field_codes": [field_code],
                    "promotion_rules": [{"slot": "document_subject", "source_paths": [source_path]}],
                },
            }
        ],
        "taxonomy_ref": {
            "master_taxonomy": {
                "categories": [{"code": "other"}],
                "cell_codes": [{"code": "other"}],
                "document_types": [{"code": "business_email"}],
                "domains": [{"code": "email"}],
                "field_codes": [{"code": field_code}],
                "promotion_slots": [{"slot": "document_subject", "label": "Document Subject"}],
                "row_types": [{"code": "other"}],
                "subcategories": [{"code": "other"}],
                "taxonomy_id": f"taxonomy.{projection_id}",
                "taxonomy_version": "v1",
            },
            "taxonomy_fingerprint": f"sha256:taxonomy_{projection_id}",
            "taxonomy_id": f"taxonomy.{projection_id}",
            "taxonomy_version": "v1",
        },
    }


def _verbose_release(projection_id: str, document_label: str) -> dict:
    return {
        "projection_refs": [
            {
                "projection_fingerprint": f"sha256:{projection_id}",
                "projection_id": projection_id,
                "projection_payload": {
                    "domain_ids": ["reflective_longform_domain"],
                    "include_document_types": ["reflective_longform_page"],
                    "include_subcategories": ["extended_argument_section"],
                    "include_field_codes": ["interpretive_contextual_anchor"],
                    "include_row_types": ["extended_paragraph_sequence"],
                    "include_cell_codes": ["extensive_comparative_interpretive_passage_marker"],
                },
            }
        ],
        "taxonomy_ref": {
            "master_taxonomy": {
                "cell_codes": [
                    {
                        "code": "extensive_comparative_interpretive_passage_marker",
                        "label": "Extensive Comparative Interpretive Passage Marker With Non Truncated Closing Evidence Phrase",
                    }
                ],
                "document_types": [{"code": "reflective_longform_page", "label": document_label}],
                "domains": [{"code": "reflective_longform_domain", "label": "Reflective Longform Philosophical Domain With Book Page Evidence"}],
                "field_codes": [
                    {
                        "code": "interpretive_contextual_anchor",
                        "label": "Interpretive Contextual Anchor With Deliberately Long Semantic Name And Source Grounding",
                    }
                ],
                "row_types": [
                    {
                        "code": "extended_paragraph_sequence",
                        "label": "Extended Paragraph Sequence With Commentary Evidence And Cross Page Continuity",
                    }
                ],
                "subcategories": [
                    {
                        "code": "extended_argument_section",
                        "label": "Extended Argument Section With Reflective Closing Questions",
                    }
                ],
                "taxonomy_id": f"taxonomy.{projection_id}",
                "taxonomy_version": "v1",
            },
            "taxonomy_fingerprint": f"sha256:taxonomy_{projection_id}",
            "taxonomy_id": f"taxonomy.{projection_id}",
            "taxonomy_version": "v1",
        },
    }
