from __future__ import annotations


PIPELINE_BATCH_NESTED_SHAPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "active_database": (
        ("database_id", "database_path", "database_fingerprint", "database_path_hash"),
        (),
    ),
    "artifact_root": (
        (
            "artifact_root_path",
            "artifact_root_fingerprint",
            "input_path",
            "documents_path",
            "corpus_path",
            "semantic_release_path",
        ),
        (),
    ),
    "semantic_release": (
        (
            "semantic_release_id",
            "semantic_release_version",
            "release_fingerprint",
            "taxonomy_id",
            "taxonomy_version",
            "taxonomy_fingerprint",
        ),
        (),
    ),
    "active_projections[]": (("projection_id", "projection_fingerprint"), ()),
    "input_files[]": (
        (
            "input_file_id",
            "input_relative_path",
            "original_ref",
            "content_hash",
            "size_bytes",
            "source_kind",
            "ingest_route",
            "pre_run_location",
            "post_run_original_location",
        ),
        (),
    ),
    "owner_run_refs": (
        ("orchestrator_run_id", "orchestrator_receipt_ref"),
        ("corpus_load_receipt_refs", "embedding_receipt_refs"),
    ),
    "output_artifacts": (
        ("raw_extracts", "structured", "normalized", "validation", "page_images", "requests", "error_cases"),
        (),
    ),
    "materialized_records[]": (
        ("document_id", "record_id", "record_semantic_materialization_ref"),
        ("embedding_ref", "artifact_refs"),
    ),
    "record_counts": (
        ("documents", "normalized_records", "projected_records", "embeddings", "error_cases"),
        (),
    ),
    "cleanup_eligibility": (
        (
            "is_cleanup_targetable",
            "cleanup_scope",
            "requires_confirmation",
            "non_deletable_refs",
            "reason_if_not_targetable",
        ),
        (),
    ),
}
