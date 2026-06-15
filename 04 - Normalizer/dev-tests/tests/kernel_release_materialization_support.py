from __future__ import annotations
import hashlib, json
from pathlib import Path
from normalizer_vision.release_runtime import build_release_runtime
from normalizer_vision.source_authoring.operations import dispatch
MODULE_ROOT = Path(__file__).resolve().parents[2]

def _owner_request(owner_action: str, **fields: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "kernel.pipeline_owner_request.v1",
        "owner_action": owner_action,
        "workflow_run_id": "wr_norm",
        "adapter_call_id": "adc_norm",
        "requested_at": "2026-05-06T00:00:00Z",
        "target_identity": {},
        **fields,
    }
    payload["request_fingerprint"] = _request_fingerprint(payload)
    return payload

def _request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

def _runtime_profile_fingerprint(release: dict[str, object]) -> str:
    runtime = build_release_runtime(release)
    projection_id = str(release["projection_ids"][0])
    return runtime.profiles[projection_id].projection_fingerprint

def _projection_precursor() -> dict[str, object]:
    return {
        "projection_id": "finance.receipts.v1",
        "label": "Finance Receipts",
        "description": "Receipt-oriented finance projection.",
        "domain_ids": ["finance"],
        "include_document_types": ["invoice", "other"],
        "include_categories": ["finance", "other"],
        "include_subcategories": ["other"],
        "include_field_codes": ["amount_due", "other"],
        "include_row_types": ["line_item", "other"],
        "include_cell_codes": ["description", "other"],
        "routing": {
            "when_to_use": "Use for invoice and receipt-like finance documents.",
            "avoid_when": "Avoid for documents without monetary or invoice evidence.",
            "example_document_types": ["invoice"],
            "section_roles": ["body"],
            "party_roles": ["other"],
        },
        "routing_lexicon": {"text_markers": ["invoice", "amount"], "domain_markers": {"finance": ["amount"]}},
    }

def _story_projection_precursor() -> dict[str, object]:
    return {
        "projection_id": "creative_writing.short_story_text.v1",
        "label": "Creative Writing Short Story Text",
        "description": "Short story projection for paragraph prose.",
        "domain_ids": ["creative_writing"],
        "include_document_types": ["short_story", "other"],
        "include_categories": ["fantasy_fiction_content", "other"],
        "include_subcategories": ["other"],
        "include_field_codes": ["story_title", "primary_setting", "fantasy_element", "narrator_voice", "other"],
        "include_row_types": ["story_paragraph", "other"],
        "include_cell_codes": ["narration_text", "other"],
        "routing": {
            "when_to_use": "Use for standalone short stories.",
            "avoid_when": "Avoid for non-fiction documents.",
            "example_document_types": ["short_story"],
            "section_roles": ["body"],
            "party_roles": ["other"],
        },
        "routing_lexicon": {"text_markers": ["story"], "domain_markers": {"creative_writing": ["story"]}},
    }

def _story_release_ref() -> dict[str, object]:
    return {
        "release_id": "custom.story.release",
        "release_version": "custom.v1",
        "release_fingerprint": "candidate-fingerprint",
        "taxonomy_ref": _custom_taxonomy_ref(),
        "projection_refs": [
            {
                "projection_id": "creative_writing.short_story_text.v1",
                "projection_fingerprint": "proj-story-fp",
                "included_taxonomy_codes": ["short_story", "story_title", "primary_setting", "fantasy_element", "narrator_voice", "story_paragraph", "narration_text", "other"],
            }
        ],
        "runtime_locale": "en",
    }

def _custom_taxonomy_ref() -> dict[str, object]:
    return {
        "taxonomy_id": "custom.story.taxonomy",
        "taxonomy_fingerprint": "sha256:custom-story-taxonomy",
        "runtime_locale": "en",
        "domains": [{"code": "creative_writing"}, {"code": "other"}],
        "document_types": [
            {"code": "short_story", "domains": ["creative_writing"]},
            {"code": "other", "domains": ["other"]},
        ],
        "categories": [
            {"code": "fantasy_fiction_content", "domains": ["creative_writing"]},
            {"code": "other", "domains": ["other"]},
        ],
        "subcategories": [{"code": "other", "domains": ["other"]}],
        "field_codes": [
            {"code": "story_title", "domains": ["creative_writing"], "value_type": "string", "promotion_slot": "story_title"},
            {"code": "primary_setting", "domains": ["creative_writing"], "value_type": "string", "promotion_slot": "primary_setting"},
            {"code": "fantasy_element", "domains": ["creative_writing"], "value_type": "string", "promotion_slot": "fantasy_element"},
            {"code": "narrator_voice", "domains": ["creative_writing"], "value_type": "string", "promotion_slot": "narrator_voice"},
            {"code": "other", "domains": ["other"], "value_type": "string"},
        ],
        "promotion_slots": [
            {
                "slot": "story_title",
                "label": "Story Title",
                "description": "Human-readable story title when available.",
                "value_type": "string",
                "scope": "document",
                "cardinality": "single",
                "query_role": "primary",
                "display_rank": 10,
            },
            {
                "slot": "primary_setting",
                "label": "Primary Setting",
                "description": "Main setting or story world anchoring the narrative.",
                "value_type": "string",
                "scope": "document",
                "cardinality": "single",
                "query_role": "primary",
                "display_rank": 20,
            },
            {
                "slot": "fantasy_element",
                "label": "Fantasy Element",
                "description": "Magic, creature, artifact or impossible phenomenon central to the story.",
                "value_type": "string",
                "scope": "document",
                "cardinality": "multi",
                "query_role": "secondary",
                "display_rank": 30,
            },
            {
                "slot": "narrator_voice",
                "label": "Narrator Voice",
                "description": "Dominant narration voice for the story.",
                "value_type": "string",
                "scope": "document",
                "cardinality": "single",
                "query_role": "secondary",
                "display_rank": 40,
            },
        ],
        "row_types": [
            {"code": "story_paragraph", "domains": ["creative_writing"], "recommended_cell_codes": ["narration_text", "other"]},
            {"code": "other", "domains": ["other"], "recommended_cell_codes": ["other"]},
        ],
        "cell_codes": [
            {"code": "narration_text", "domains": ["creative_writing"], "value_type": "string"},
            {"code": "other", "domains": ["other"], "value_type": "string"},
        ],
        "taxonomy_text": {
            "terms": {
                "field_codes": [
                    {"code": "story_title", "label": "Story title", "description": "Title of the story.", "aliases": []}
                ]
            }
        },
    }

def _base_release_payload() -> dict[str, object]:
    master = {
        "taxonomy_id": "normalizer_taxonomy.master",
        "taxonomy_version": "2026-test",
        "domains": [{"id": "finance", "label": "Finance", "description": "Finance documents."}, {"id": "other", "label": "Other", "description": "Fallback."}],
        "document_types": [{"code": "invoice", "label": "Invoice", "description": "Invoice documents.", "domains": ["finance"]}, {"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
        "categories": [{"code": "finance", "label": "Finance", "description": "Finance.", "domains": ["finance"]}, {"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
        "subcategories": [{"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
        "field_codes": [{"code": "amount_due", "label": "Amount due", "description": "Payable amount.", "domains": ["finance"]}, {"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
        "row_types": [{"code": "line_item", "label": "Line item", "description": "Invoice row.", "domains": ["finance"]}, {"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
        "cell_codes": [{"code": "description", "label": "Description", "description": "Description cell.", "domains": ["finance"]}, {"code": "other", "label": "Other", "description": "Fallback.", "domains": ["other"]}],
    }
    return {
        "schema_version": "1.0",
        "release_id": "semantic_release.default",
        "release_version": "2026-test",
        "master_taxonomy_id": "normalizer_taxonomy.master",
        "master_taxonomy_version": "2026-test",
        "master_taxonomy_release_id": "sha256:master-test",
        "runtime_locale": "en",
        "projection_ids": [],
        "materialization_version": "1",
        "created_at": "2026-05-26T00:00:00Z",
        "fingerprint": "sha256:base-test",
        "master_taxonomy": master,
        "projections": [],
    }
