from __future__ import annotations

from typing import Any


def compatibility_review(delta_type: str) -> dict[str, Any]:
    if delta_type == "new_taxonomy_fields_likely":
        return {
            "requires_revision_classification": True,
            "likely_change_class": "master_taxonomy_changed_if_fields_are_added",
            "backfill_supported": False,
            "requires_reset_or_new_db_if_applied_to_non_empty_db": True,
            "safe_decision_points": [
                "Review working-release field proposal before writing.",
                "Validate, compile, and export the candidate release.",
                "Run activation_preflight and classify_release_revision before activation.",
                "If the master taxonomy changes on a non-empty DB, use a new DB or reset and reimport old source documents.",
                "Before reset/new DB switch, preview/prepare old source originals through corpus_source_reimport; do not ask the user to sort Documents/originals manually.",
            ],
            "user_message_de": "Wenn daraus neue Archivfelder werden, ist das wahrscheinlich eine neue Taxonomie-Linie. Auf einer bestehenden DB reicht Backfill dann nicht: alte Quelldokumente muessen in die neue Taxonomie neu eingelesen werden, oder du baust eine neue DB auf.",
        }
    if delta_type in {"projection_or_routing_gap_likely", "projection_guidance_may_need_refinement"}:
        return {
            "requires_revision_classification": True,
            "likely_change_class": "same_master_or_projection_incompatible",
            "backfill_supported": "only_if_classify_release_revision_reports_same_master_release_revision",
            "requires_reset_or_new_db_if_applied_to_non_empty_db": "only_if_projection_selection_becomes_incompatible",
            "safe_decision_points": [
                "Review projection/routing change before writing.",
                "Validate, compile, export, then run activation_preflight.",
                "Use classify_release_revision to decide between same-master backfill and reset/new DB.",
            ],
            "user_message_de": "Wenn nur Profilwahl oder Routing geschaerft wird, kann die bestehende DB eventuell bleiben. Das entscheidet aber erst die Release-Revision-Pruefung; bei inkompatibler Projection-Auswahl braucht es Reset/Re-Import oder eine neue DB.",
        }
    return {
        "requires_revision_classification": False,
        "likely_change_class": "no_change_or_minor_review",
        "backfill_supported": False,
        "requires_reset_or_new_db_if_applied_to_non_empty_db": False,
        "safe_decision_points": ["No release change is implied by this read-only review."],
        "user_message_de": "Aus dieser Sicht ist keine strukturelle Taxonomie-Aenderung erkennbar.",
    }
