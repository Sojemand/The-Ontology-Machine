from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from semantic_control_kernel.adapters.corpus import CorpusAdapter
from semantic_control_kernel.adapters.embedding import EmbeddingAdapter
from semantic_control_kernel.adapters.merge import MergeAdapter
from semantic_control_kernel.adapters.pipeline_batch import PipelineBatchAdapter
from semantic_control_kernel.adapters.semantic_release import SemanticReleaseAdapter
from semantic_control_kernel.adapters.workspace import WorkspaceAdapter
from semantic_control_kernel.types.adapter_results import AdapterCallResult

MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
sys.path.insert(0, str(PIPELINE_ROOT / "05 - Corpus Builder"))

from corpus_builder.database.repository_connection import connect
from corpus_builder.database.workflow import ensure_schema

def _adapters(tmp_path: Path):
    kwargs = {"state_root": tmp_path / "state", "pipeline_root": PIPELINE_ROOT}
    return (
        WorkspaceAdapter(**kwargs),
        CorpusAdapter(**kwargs),
        SemanticReleaseAdapter(**kwargs),
        PipelineBatchAdapter(**kwargs),
        MergeAdapter(**kwargs),
    )

def _seed_analysis_database(artifact_root: Path) -> None:
    database_path = artifact_root / "Corpus" / "active.db"
    normalized_path = artifact_root / "Documents" / "normalized" / "doc_1.json"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text("{}", encoding="utf-8")
    conn = connect(str(database_path))
    try:
        ensure_schema(conn)
        conn.execute(
            """
            UPDATE installation_state
            SET active_release_id = ?, active_release_version = ?, active_release_fingerprint = ?, updated_at = CURRENT_TIMESTAMP
            WHERE singleton = 1
            """,
            ("release_a", "v1", "fp_release"),
        )
        conn.execute(
            """
            INSERT INTO documents (
                id, file_name, file_path, source_file_path, content_hash, document_type, category, model, model_confidence,
                needs_review, normalizer_needs_review, projection_id, projection_fingerprint, validator_status, validator_issues_count, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "invoice.pdf",
                str(normalized_path),
                str(artifact_root / "Documents" / "originals" / "invoice.pdf"),
                "hash_doc_1",
                "invoice",
                "finance",
                "test-model",
                0.99,
                1,
                1,
                "projection_a",
                "fp_projection_a",
                "warning",
                2,
            ),
        )
        conn.execute(
            """
            INSERT INTO document_payloads (
                document_id, schema_version, structured_json, normalized_json, projection_json, release_fingerprint, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "kernel.document_payload.v1",
                '{"structured": true}',
                '{"normalized": true}',
                '{"projection": true}',
                "fp_release",
            ),
        )
        conn.execute(
            """
            INSERT INTO document_processing_state (
                document_id, schema_version, materialization_version, materialized_snapshot_id, projection_id,
                projection_fingerprint, materialization_state, source_mode, last_materialized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "doc_1",
                "kernel.document_processing_state.v1",
                "mv1",
                "snapshot_1",
                "projection_a",
                "fp_projection_a",
                "current",
                "structured",
            ),
        )
        conn.execute(
            "INSERT INTO evidence_atoms (document_id, atom_type, json_path, source_ref, text_value) VALUES (?, ?, ?, ?, ?)",
            ("doc_1", "field", "$.total", "Documents/structured/invoice.structured.json", "19.99"),
        )
        conn.execute(
            """
            INSERT INTO slot_candidates (document_id, slot, display_value, strategy, confidence, is_projection_backed, source_refs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("doc_1", "total_amount", "19.99", "semantic_projection", 0.92, 1, '["Documents/structured/invoice.structured.json"]'),
        )
        conn.execute(
            """
            INSERT INTO document_entities (
                document_id, entity_key, entity_type, display_value, source_path, projection_id, materialization_version, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("doc_1", "invoice.total", "amount", "19.99", "content.fields.total_amount", "projection_a", "mv1", "materialized"),
        )
        conn.execute(
            "INSERT INTO materialization_audit (created_at, level, code, document_id, projection_id, message, details_json) VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)",
            ("warning", "projection_gap", "doc_1", "projection_a", "Projected field needs review.", "{}"),
        )
        conn.commit()
    finally:
        conn.close()

def _request_fingerprint(payload: dict[str, object]) -> str:
    seed = dict(payload)
    seed["request_fingerprint"] = ""
    canonical = json.dumps(seed, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

def _story_projection_precursor() -> dict[str, object]:
    return {
        "projection_id": "creative_writing.short_story_text.v1",
        "label": "Creative Writing Short Story Text",
        "description": "Short story projection for paragraph prose.",
        "domain_ids": ["creative_writing"],
        "include_document_types": ["short_story", "other"],
        "include_categories": ["fantasy_fiction_content", "other"],
        "include_subcategories": ["other"],
        "include_field_codes": ["story_title", "other"],
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
            {"code": "story_title", "domains": ["creative_writing"], "value_type": "string"},
            {"code": "other", "domains": ["other"], "value_type": "string"},
        ],
        "row_types": [
            {"code": "story_paragraph", "domains": ["creative_writing"], "recommended_cell_codes": ["narration_text", "other"]},
            {"code": "other", "domains": ["other"], "recommended_cell_codes": ["other"]},
        ],
        "cell_codes": [
            {"code": "narration_text", "domains": ["creative_writing"], "value_type": "string"},
            {"code": "other", "domains": ["other"], "value_type": "string"},
        ],
    }
