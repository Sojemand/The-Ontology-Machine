from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _artifact_properties, _enum, _tool

_TIMEOUT_SECONDS = {
    "type": "integer",
    "minimum": 1,
    "default": 120,
    "description": "MCP subprocess timeout; not forwarded as Corpus Builder product payload.",
}


def artifact_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "corpus_builder.load_document",
            "Load exactly one normalized artifact set into an existing corpus.db by delegating once to 05 - Corpus Builder load_document. MCP validates artifact and DB path boundaries, but does not implement Corpus persistence, materialization, or embedding logic.",
            {
                "artifact_root": {
                    "type": "string",
                    "description": "Existing root that must contain the normalized, structured, validation, optional raw, and optional page-image paths.",
                },
                "normalized_path": {"type": "string"},
                "structured_path": {"type": "string"},
                "validation_path": {"type": "string"},
                "raw_path": {"type": "string"},
                "corpus_db_path": {"type": "string"},
                "corpus_output_folder": {
                    "type": "string",
                    "description": "Existing Corpus Builder output folder that must contain corpus_db_path.",
                },
                "persist_page_images_in_db": {"type": "boolean"},
                "page_images_dir": {"type": "string"},
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=(
                "artifact_root",
                "normalized_path",
                "structured_path",
                "validation_path",
                "corpus_db_path",
                "corpus_output_folder",
            ),
        ),
        _tool(
            "corpus_builder.healthcheck",
            "Check Corpus Builder runtime and contract health through corpus_builder.orchestrator_contract. Embedding provider readiness remains owner-reported and optional.",
            {
                "runtime_model": {
                    "type": "string",
                    "description": "Embedding runtime model passed as Corpus Builder runtime_settings.model for owner health diagnostics.",
                },
                "scope": {
                    "type": "string",
                    "description": "Optional owner healthcheck scope such as pipeline_run.",
                },
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("runtime_model",),
        ),
        _tool(
            "corpus_builder.scan_debug_input",
            "Scan one Corpus Builder artifact input folder for the debug host by delegating to 05 - Corpus Builder scan_debug_input. MCP bounds the input root and debug session write root.",
            {
                "input_root": {"type": "string"},
                "debug_root": {"type": "string"},
                "session_root": {
                    "type": "string",
                    "description": "Debug session folder, absolute or relative to debug_root. Owner writes scan artifacts below this folder.",
                },
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("input_root", "debug_root", "session_root"),
        ),
        _tool("preview_rebuild_from_artifacts", "Preview a Corpus Builder artifact rebuild.", _artifact_properties()),
        _tool(
            "rebuild_corpus_from_artifacts",
            "Rebuild a corpus DB from artifacts through Corpus Builder only. Activate any release separately before rebuilding.",
            {
                **_artifact_properties(),
                "replace_existing": {"type": "boolean", "default": True},
            },
        ),
        _tool(
            "generate_embeddings",
            "Generate embeddings through Corpus Builder with explicit runtime model settings.",
            {"corpus_db_path": {"type": "string"}, "runtime_model": {"type": "string"}},
            required=("corpus_db_path", "runtime_model"),
        ),
        _tool(
            "search_corpus",
            "Search the corpus via Corpus Builder. After a test import, use targeted searches for expected names, labels, or concepts to sanity-check whether the active release made the archive useful.",
            {
                "query": {"type": "string"},
                "mode": {"type": "string", "enum": ["Fulltext", "Semantisch", "Hybrid"], "default": "Fulltext"},
                "limit": {"type": "integer", "minimum": 1},
                "corpus_db_path": {"type": "string"},
                "runtime_model": {"type": "string"},
            },
            required=("query",),
        ),
        _tool("corpus_stats", "Load corpus stats via Corpus Builder.", {"corpus_db_path": {"type": "string"}}),
        _tool(
            "export_corpus",
            "Export the corpus to JSONL or CSV via Corpus Builder.",
            {
                "output_path": {"type": "string"},
                "fmt": {"type": "string", "enum": ["jsonl", "csv"], "default": "jsonl"},
                "include_archived": {"type": "boolean", "default": False},
                "corpus_db_path": {"type": "string"},
            },
            required=("output_path",),
        ),
    ]
