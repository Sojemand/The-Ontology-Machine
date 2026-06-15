from __future__ import annotations

from typing import Any

from .tool_catalog_utils import _tool
from .tool_catalog_normalizer_authoring import normalizer_authoring_tools
from .tool_catalog_normalizer_glossary import translation_glossary_tools

_RUNTIME_SETTINGS = {
    "type": "object",
    "properties": {
        "model": {"type": "string", "description": "Request-owned Normalizer provider model."},
        "max_output_tokens": {"type": "integer", "minimum": 1},
    },
    "required": ["model", "max_output_tokens"],
    "additionalProperties": False,
}
_TIMEOUT_SECONDS = {
    "type": "integer",
    "minimum": 1,
    "default": 1800,
    "description": "MCP subprocess timeout; not forwarded as Normalizer runtime truth.",
}
_RELEASE_CONTEXT_OUTPUT = {
    "type": "object",
    "properties": {
        "checked": {"type": "boolean"},
        "source": {"type": "string"},
        "corpus_db_path": {"type": "string"},
        "release_id": {"type": "string"},
        "release_version": {"type": "string"},
        "fingerprint": {"type": "string"},
        "active_snapshot_id": {"type": "string"},
        "runtime_truth_source": {"type": "string"},
    },
    "required": ["checked", "source"],
    "additionalProperties": False,
}
_NORMALIZE_OUTPUT = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "output_path": {"type": ["string", "null"]},
        "needs_review": {"type": "boolean"},
        "message": {"type": "string"},
        "review_reason": {"type": "string"},
        "duration_ms": {"type": "integer"},
        "release_context": _RELEASE_CONTEXT_OUTPUT,
    },
    "required": ["status", "release_context"],
    "additionalProperties": True,
}
_HEALTHCHECK_OUTPUT = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "healthy": {"type": "boolean"},
        "message": {"type": "string"},
        "dependencies": {"type": "array", "items": {"type": "object"}},
        "release_context": _RELEASE_CONTEXT_OUTPUT,
    },
    "required": ["status", "release_context"],
    "additionalProperties": True,
}


def normalizer_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "normalizer.normalize_document",
            "Normalize exactly one *.structured.json by first reading the active Semantic Release snapshot from 05 - Corpus Builder and then delegating once to 04 - Normalizer normalize_document. MCP consumes the runtime truth and never accepts, builds, publishes, or persists a release payload.",
            {
                "structured_path": {"type": "string"},
                "structured_root": {"type": "string", "description": "Existing root that must contain structured_path."},
                "normalized_output_path": {"type": "string"},
                "normalized_root": {"type": "string", "description": "Existing root that must contain normalized_output_path."},
                "corpus_db_path": {"type": "string", "description": "Corpus DB whose active snapshot is the release runtime truth."},
                "corpus_output_folder": {
                    "type": "string",
                    "description": "Optional storage root that must contain corpus_db_path; defaults to the DB parent.",
                },
                "runtime_settings": _RUNTIME_SETTINGS,
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=(
                "structured_path",
                "structured_root",
                "normalized_output_path",
                "normalized_root",
                "corpus_db_path",
                "runtime_settings",
            ),
            output_schema=_NORMALIZE_OUTPUT,
        ),
        _tool(
            "normalizer.healthcheck",
            "Check Normalizer provider/runtime readiness through 04 - Normalizer healthcheck. When corpus_db_path is provided, MCP also reads the active Corpus Builder release snapshot so release-context problems are visible without creating release authoring or publish work.",
            {
                "runtime_settings": _RUNTIME_SETTINGS,
                "corpus_db_path": {"type": "string", "description": "Optional corpus DB whose active release context should be checked."},
                "corpus_output_folder": {
                    "type": "string",
                    "description": "Optional storage root that must contain corpus_db_path; defaults to the DB parent.",
                },
                "timeout_seconds": _TIMEOUT_SECONDS,
            },
            required=("runtime_settings",),
            output_schema=_HEALTHCHECK_OUTPUT,
        ),
        _tool(
            "list_default_blueprints",
            "List checked-in immutable default extraction blueprints via the Normalizer edit contract. This does not derive a working source package, validate, compile, export, or activate.",
            {},
        ),
        _tool(
            "inspect_source_document_sample",
            "Run a read-only Optimizer inspection on one user-provided source document and return compact excerpts, headings, field-like phrases, and candidate markers. Use this before designing a custom/special-purpose archive when the user gives an example document path. Explain that the document content will be inspected locally to improve the suggested profiles and fields; this does not create a DB, import the document, or activate an extraction pack.",
            {
                "source_document_path": {"type": "string", "description": "Absolute path to one example source document."},
                "sample_label": {"type": "string", "description": "Optional user-facing label for the sample."},
                "max_excerpt_chars": {"type": "integer", "minimum": 1, "default": 6000, "description": "Maximum source text characters to return to the agent."},
                "timeout_seconds": {"type": "integer", "minimum": 1, "default": 120},
                "cleanup_days": {"type": "integer", "minimum": 0, "default": 1, "description": "Delete older inspection temp folders before running."},
            },
            required=("source_document_path",),
        ),
        _tool(
            "export_default_blueprint_release",
            "Export the general default extraction package as a JSON bundle to an explicit user/workspace path. Explain first that this uses the standard document profiles and is not a custom taxonomy.",
            {
                "blueprint_ref": {"type": "string", "default": "default"},
                "target_locale": {"type": "string", "description": "Locale for field labels and extraction guidance; not necessarily the language of every source document."},
                "output_path": {"type": "string", "description": "Explicit JSON target path outside the MCP Server state directory."},
            },
            required=("output_path",),
        ),
        *normalizer_authoring_tools(),
        *translation_glossary_tools(),
    ]
