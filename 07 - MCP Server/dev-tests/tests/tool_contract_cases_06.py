from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_incident, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "backfill_stale",
            lambda p: {"corpus_db_path": p["active_db"], "document_ids": ["doc-1", "doc-2"], "stale_only": True, "limit": 2},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "backfill_stale",
                        "corpus_db_path": p["active_db"],
                        "document_ids": ["doc-1", "doc-2"],
                        "stale_only": True,
                        "limit": 2,
                    },
                )
            ],
        ),
        GoldenCase(
            "merge_preflight",
            lambda p: {"source_db_path": p["source_db"], "target_db_path": p["target_db"]},
            product_calls=lambda p: [
                ("corpus_builder", {"action": "merge_preflight", "source_db_path": p["source_db"], "target_db_path": p["target_db"]})
            ],
        ),
        GoldenCase(
            "merge_corpora",
            lambda p: {
                "source_db_path": p["source_db"],
                "target_db_path": p["target_db"],
                "snapshot_risk_confirmation_artifact_path": p["snapshot_confirmation"],
                "collision_resolution_artifact_path": p["collision_resolution"],
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "merge_corpus_databases",
                        "source_db_path": p["source_db"],
                        "target_db_path": p["target_db"],
                        "snapshot_risk_confirmation_artifact_path": p["snapshot_confirmation"],
                        "collision_resolution_artifact_path": p["collision_resolution"],
                    },
                )
            ],
        ),
        GoldenCase(
            "preview_rebuild_from_artifacts",
            lambda p: _artifact_args(p),
            product_calls=lambda p: [("corpus_builder", {"action": "preview_rebuild_from_artifacts", **_artifact_args(p)})],
        ),
        GoldenCase(
            "rebuild_corpus_from_artifacts",
            lambda p: {"replace_existing": False, **_artifact_args(p)},
            product_calls=lambda p: [
                ("corpus_builder", {"action": "rebuild_from_artifacts", **_artifact_args(p), "replace_existing": False})
            ],
        ),
        GoldenCase(
            "generate_embeddings",
            lambda p: {"corpus_db_path": p["active_db"], "runtime_model": "text-embedding-3-small"},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "generate_embeddings",
                        "corpus_db_path": p["active_db"],
                        "runtime_model": "text-embedding-3-small",
                    },
                )
            ],
        ),
        GoldenCase(
            "search_corpus",
            lambda p: {"query": "invoice", "mode": "Hybrid", "limit": 5, "corpus_db_path": p["active_db"], "runtime_model": "embed"},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "search",
                        "query": "invoice",
                        "mode": "Hybrid",
                        "corpus_db_path": p["active_db"],
                        "runtime_model": "embed",
                        "limit": 5,
                    },
                )
            ],
        ),
        GoldenCase(
            "corpus_stats",
            lambda p: {"corpus_db_path": p["active_db"]},
            product_calls=lambda p: [("corpus_builder", {"action": "stats", "corpus_db_path": p["active_db"]})],
        ),
        GoldenCase(
            "export_corpus",
            lambda p: {"output_path": p["export_path"], "fmt": "jsonl", "include_archived": True, "corpus_db_path": p["active_db"]},
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {
                        "action": "export",
                        "output_path": p["export_path"],
                        "fmt": "jsonl",
                        "include_archived": True,
                        "corpus_db_path": p["active_db"],
                    },
                )
            ],
        ),
        GoldenCase(
            "inspect_runtime",
            lambda _p: {},
            admin_calls=lambda _p: [("orchestrator", {"action": "inspect_runtime"})],
        ),
        GoldenCase(
            "read_runtime_settings",
            lambda _p: {},
            admin_calls=lambda _p: [
                ("orchestrator", {"action": "manage_runtime_settings", "operation": "read"})
            ],
        ),
        GoldenCase(
            "write_runtime_settings",
            lambda _p: {"settings": {"llm_model": "gpt-test"}},
            admin_calls=lambda _p: [
                ("orchestrator", {"action": "manage_runtime_settings", "operation": "write", "settings": {"llm_model": "gpt-test"}})
            ],
        ),
        GoldenCase(
            "reset_runtime_settings",
            lambda _p: {},
            admin_calls=lambda _p: [
                ("orchestrator", {"action": "manage_runtime_settings", "operation": "reset"})
            ],
        ),
    ]
