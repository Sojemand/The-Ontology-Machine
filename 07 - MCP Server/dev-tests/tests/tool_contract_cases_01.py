from __future__ import annotations

from tests.tool_contract_matrix_helpers import _artifact_args, _reset_workspace_paths, _support_assessment, _support_incident, _support_queue_args, _working_workspace_paths, _workspace_paths
from tests.tool_contract_matrix_types import GoldenCase


def cases() -> list[GoldenCase]:
    return [
        GoldenCase("mcp_server.describe_surfaces", lambda _p: {}),
        GoldenCase("mcp_server.read_surface", lambda _p: {"surface_id": "mcp_server.support_monitor"}),
        GoldenCase("mcp_server.healthcheck", lambda _p: {}),
        GoldenCase("inspect_pipeline_contract_governance", lambda _p: {}),
        GoldenCase("inspect_agent_permissions", lambda _p: {}),
        GoldenCase("inspect_support_monitor_summary", lambda _p: {}),
        GoldenCase(
            "assess_support_incident",
            lambda _p: {
                "classification": "unexpected_exception",
                "confidence": "high",
                "module_key": "normalizer",
                "tool_action": "compile_release_package",
                "severity": "error",
                "status": "exception",
                "message": "Compile failed for user C:\\Users\\Norma with token sk-testsecretvalue123456",
                "exception_type": "RuntimeError",
                "stacktrace": "Traceback...\nRuntimeError: compile failed",
                "metadata": {"api_key": "secret", "stage": "compile"},
            },
        ),
        GoldenCase("list_support_incidents", lambda _p: {}),
        GoldenCase("preview_support_bug_report", lambda p: {"assessment_id": _support_assessment(p)}),
        GoldenCase("build_support_bug_report", lambda p: {"assessment_id": _support_assessment(p), "output_path": p["bug_report_path"]}),
        GoldenCase("queue_support_bug_report", _support_queue_args),
        GoldenCase("dismiss_support_incident", lambda p: {"incident_id": _support_incident(p), "reason": "contract matrix"}),
        GoldenCase(
            "describe_owner_surfaces",
            lambda _p: {"module": "orchestrator"},
            edit_calls=lambda _p: [("orchestrator", {"action": "describe_surfaces"})],
        ),
        GoldenCase(
            "read_owner_bundle",
            lambda _p: {"module": "normalizer"},
            edit_calls=lambda _p: [("normalizer", {"action": "read_bundle"})],
        ),
        GoldenCase(
            "read_owner_surface",
            lambda _p: {"module": "orchestrator", "surface_id": "orchestrator.execution_policy"},
            edit_calls=lambda _p: [
                ("orchestrator", {"action": "read_surface", "surface_id": "orchestrator.execution_policy"})
            ],
        ),
        GoldenCase(
            "validate_owner_surface",
            lambda _p: {"module": "normalizer", "surface_id": "normalizer.release", "value": {"enabled": True}},
            edit_calls=lambda _p: [
                (
                    "normalizer",
                    {"action": "validate_surface", "surface_id": "normalizer.release", "value": {"enabled": True}},
                )
            ],
        ),
        GoldenCase(
            "write_owner_surface",
            lambda _p: {"module": "orchestrator", "surface_id": "orchestrator.execution_policy", "value": {"enabled": True}},
            edit_calls=lambda _p: [
                (
                    "orchestrator",
                    {"action": "write_surface", "surface_id": "orchestrator.execution_policy", "value": {"enabled": True}},
                )
            ],
        ),
        GoldenCase(
            "corpus_builder.describe_surfaces",
            lambda _p: {},
            edit_calls=lambda _p: [("corpus_builder", {"action": "describe_surfaces"})],
        ),
        GoldenCase(
            "corpus_builder.read_surface",
            lambda _p: {"surface_id": "corpus_builder.settings"},
            edit_calls=lambda _p: [
                ("corpus_builder", {"action": "read_surface", "surface_id": "corpus_builder.settings"})
            ],
        ),
        GoldenCase(
            "corpus_builder.validate_surface",
            lambda _p: {"surface_id": "corpus_builder.embeddings_policy", "value": {"embeddings.dimensions": 1536}},
            edit_calls=lambda _p: [
                (
                    "corpus_builder",
                    {
                        "action": "validate_surface",
                        "surface_id": "corpus_builder.embeddings_policy",
                        "value": {"embeddings.dimensions": 1536},
                    },
                )
            ],
        ),
        GoldenCase(
            "corpus_builder.write_surface",
            lambda _p: {"surface_id": "corpus_builder.search_policy", "value": {"fulltext.limit_default": 10}},
            edit_calls=lambda _p: [
                (
                    "corpus_builder",
                    {
                        "action": "write_surface",
                        "surface_id": "corpus_builder.search_policy",
                        "value": {"fulltext.limit_default": 10},
                    },
                )
            ],
        ),
        GoldenCase(
            "list_default_blueprints",
            lambda _p: {},
            product_calls=lambda _p: [("normalizer", {"action": "list_default_blueprints"})],
        ),
        GoldenCase(
            "inspect_source_document_sample",
            lambda p: {"source_document_path": p["sample_document"], "max_excerpt_chars": 5000},
            product_calls=lambda p: [
                (
                    "orchestrator",
                    {
                        "action": "inspect_source_document_sample",
                        "source_document_path": p["sample_document"],
                        "max_excerpt_chars": 5000,
                    },
                )
            ],
        ),
        GoldenCase(
            "assess_source_document_fit",
            lambda p: {
                "source_document_path": p["sample_document"],
                "corpus_db_path": p["active_db"],
                "max_excerpt_chars": 5000,
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": p["active_db"]},
                ),
                (
                    "orchestrator",
                    {
                        "action": "inspect_source_document_sample",
                        "source_document_path": p["sample_document"],
                        "max_excerpt_chars": 5000,
                    },
                ),
            ],
        ),
        GoldenCase(
            "review_source_document_taxonomy_coverage",
            lambda p: {
                "source_document_path": p["sample_document"],
                "corpus_db_path": p["active_db"],
                "max_excerpt_chars": 5000,
            },
            product_calls=lambda p: [
                (
                    "corpus_builder",
                    {"action": "read_active_semantic_release", "corpus_db_path": p["active_db"]},
                ),
                (
                    "orchestrator",
                    {
                        "action": "inspect_source_document_sample",
                        "source_document_path": p["sample_document"],
                        "max_excerpt_chars": 5000,
                    },
                ),
            ],
        ),
        GoldenCase(
            "export_default_blueprint_release",
            lambda p: {"blueprint_ref": "default", "target_locale": "en", "output_path": p["exported_release"]},
            product_calls=lambda p: [
                (
                    "normalizer",
                    {
                        "action": "export_default_blueprint_release",
                        "blueprint_ref": "default",
                        "target_locale": "en",
                        "output_path": p["exported_release"],
                    },
                )
            ],
        ),
    ]
