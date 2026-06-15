"""Document indexes for the core corpus.db contract."""

from __future__ import annotations

from .types import IndexContract

DOCUMENT_INDEXES = tuple(
    IndexContract(sql)
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_docs_file_path ON documents(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_docs_source_file_path ON documents(source_file_path);",
        "CREATE INDEX IF NOT EXISTS idx_docs_source_page ON documents(source_page);",
        "CREATE INDEX IF NOT EXISTS idx_docs_source_document ON documents(source_document_id);",
        "CREATE INDEX IF NOT EXISTS idx_docs_source_document_page ON documents(source_document_id, page_index);",
        "CREATE INDEX IF NOT EXISTS idx_docs_source_artifact ON documents(source_artifact_id);",
        "CREATE INDEX IF NOT EXISTS idx_docs_ingest_run ON documents(ingest_run_id);",
        "CREATE INDEX IF NOT EXISTS idx_docs_materialization_order ON documents(materialization_order);",
        "CREATE INDEX IF NOT EXISTS idx_docs_content_hash ON documents(content_hash);",
        "CREATE INDEX IF NOT EXISTS idx_docs_document_type ON documents(document_type);",
        "CREATE INDEX IF NOT EXISTS idx_docs_category ON documents(category);",
        "CREATE INDEX IF NOT EXISTS idx_docs_is_archived ON documents(is_archived);",
        "CREATE INDEX IF NOT EXISTS idx_docs_needs_review ON documents(needs_review);",
        "CREATE INDEX IF NOT EXISTS idx_docs_interpreter_review ON documents(interpreter_needs_review);",
        "CREATE INDEX IF NOT EXISTS idx_docs_normalizer_review ON documents(normalizer_needs_review);",
        "CREATE INDEX IF NOT EXISTS idx_docs_validator_status ON documents(validator_status);",
        "CREATE INDEX IF NOT EXISTS idx_payloads_loaded_at ON document_payloads(loaded_at);",
        "CREATE INDEX IF NOT EXISTS idx_fields_document ON extracted_fields(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_fields_key ON extracted_fields(key);",
        "CREATE INDEX IF NOT EXISTS idx_fields_key_value ON extracted_fields(key, value);",
        "CREATE INDEX IF NOT EXISTS idx_fields_numeric ON extracted_fields(key, numeric_value);",
        "CREATE INDEX IF NOT EXISTS idx_fields_normalized ON extracted_fields(normalized_value);",
        "CREATE INDEX IF NOT EXISTS idx_fields_compact ON extracted_fields(compact_value);",
        "CREATE INDEX IF NOT EXISTS idx_rows_document ON extracted_rows(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_relations_document ON relations(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);",
        "CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_document_id);",
        "CREATE INDEX IF NOT EXISTS idx_relations_origin ON relations(relation_origin);",
        "CREATE INDEX IF NOT EXISTS idx_relations_status ON relations(status);",
        "CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);",
        "CREATE INDEX IF NOT EXISTS idx_tags_normalized ON tags(normalized_tag);",
        "CREATE INDEX IF NOT EXISTS idx_tags_compact ON tags(compact_tag);",
        "CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);",
        "CREATE INDEX IF NOT EXISTS idx_people_normalized ON people(normalized_name);",
        "CREATE INDEX IF NOT EXISTS idx_people_compact ON people(compact_name);",
        "CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(name);",
        "CREATE INDEX IF NOT EXISTS idx_orgs_normalized ON organizations(normalized_name);",
        "CREATE INDEX IF NOT EXISTS idx_orgs_compact ON organizations(compact_name);",
    )
)


__all__ = ["DOCUMENT_INDEXES"]
