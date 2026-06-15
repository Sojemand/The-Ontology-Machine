from __future__ import annotations

import corpus_builder.services as services
import corpus_builder.standalone_artifacts as standalone_artifacts


def test_services_surface_exports_path_stable_entry_points() -> None:
    expected = {
        "load_module_config",
        "resolve_corpus_db_path",
        "build_load_bundle",
        "load_batch",
        "generate_embeddings",
        "search_corpus",
        "export_corpus",
        "get_stats",
        "list_archived",
        "semantic_status",
        "read_active_semantic_release",
        "load_semantic_release",
        "audit_semantics",
        "apply_semantic_release",
        "backfill_semantics",
    }

    assert expected.issubset(set(services.__all__))
    for name in expected:
        assert hasattr(services, name)


def test_standalone_artifact_surface_exports_rebuild_entry_points() -> None:
    expected = {"build_rebuild_bundles_from_artifacts", "rebuild_corpus_from_artifacts"}

    assert expected.issubset(set(standalone_artifacts.__all__))
    for name in expected:
        assert hasattr(standalone_artifacts, name)
