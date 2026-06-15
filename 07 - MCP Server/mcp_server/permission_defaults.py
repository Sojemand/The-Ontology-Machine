from __future__ import annotations

from typing import Any

from .semantic_control_kernel_visibility import PERMANENT_AGENT_TOOL_NAMES

SCHEMA_VERSION = 1
POLICY_SURFACE_ID = "mcp_server.agent_permissions"
AGENT_LEVEL_ENV_FALLBACKS = ("VISION_MCP_AGENT_LEVEL", "MCP_AGENT_LEVEL")
LEVEL_ORDER = ("L0_READONLY", "L1_AUTHOR", "L2_OPERATOR", "L3_ADMIN")
SEMANTIC_CONTROL_KERNEL_AGENT_TOOLS = tuple(PERMANENT_AGENT_TOOL_NAMES)

L0_READONLY_TOOLS = (
    *SEMANTIC_CONTROL_KERNEL_AGENT_TOOLS,
    "mcp_server.describe_surfaces", "mcp_server.healthcheck",
    "inspect_pipeline_contract_governance", "inspect_agent_permissions", "inspect_support_monitor_summary",
    "inspect_pipeline_product_context", "explain_pipeline_capabilities", "recommend_pipeline_next_steps",
    "describe_owner_surfaces", "interpreter.describe_surfaces", "interpreter.read_surface", "list_default_blueprints",
    "inspect_active_corpus", "inspect_active_workspace_status", "inspect_current_environment_status", "inspect_active_pipeline_run", "read_active_semantic_release", "verify_workspace_active_release", "semantic_audit",
    "activation_preflight", "merge_preflight", "preview_rebuild_from_artifacts", "preview_active_corpus_source_reimport", "search_corpus",
    "corpus_stats", "inspect_runtime",
    "read_revision_candidate_release", "inspect_release_revision_context", "classify_release_revision",
    "orchestrator.healthcheck",
    "optimizer.classify_document", "optimizer.healthcheck", "interpreter.healthcheck", "validator.healthcheck", "corpus_builder.healthcheck",
    "normalizer.healthcheck",
    "optimizer.describe_surfaces", "optimizer.read_surface",
    "corpus_builder.describe_surfaces", "corpus_builder.read_surface",
    "validator.describe_surfaces", "validator.read_surface",
)
L1_AUTHOR_TOOLS = (
    "export_default_blueprint_release",
    "read_working_release", "list_working_release_profiles", "read_working_release_profile",
    "validate_working_release", "compile_working_release", "preview_working_release_impact",
    "read_translation_glossary",
    "review_bootstrap_release", "review_data_informed_release",
    "export_working_release",
    "assess_support_incident", "list_support_incidents", "preview_support_bug_report",
    "build_support_bug_report", "queue_support_bug_report", "dismiss_support_incident",
    "load_semantic_release", "export_corpus",
)
L2_OPERATOR_TOOLS = (
    "assess_source_document_fit", "review_source_document_taxonomy_coverage", "review_source_sample_set_taxonomy_coverage",
    "prepare_source_samples_for_input", "inspect_source_document_sample", "derive_working_release_from_blueprint",
    "apply_bootstrap_release", "refine_working_release_from_sample",
    "create_working_release_package",
    "create_locale_scaffold", "create_minimal_custom_release",
    "create_projection_draft", "generate_locale_translation_payload", "translate_working_release_locale",
    "upsert_translation_glossary_entry", "remove_translation_glossary_entry",
    "activate_corpus_context", "create_empty_corpus_db", "prepare_pipeline_workspace_root",
    "write_workspace_release_change_confirmation", "write_workspace_db_reset_confirmation",
    "orchestrator.reset",
    "optimizer.extract_document", "optimizer.scan_debug_input",
    "interpreter.interpret_document", "validator.validate_document",
    "corpus_builder.load_document", "corpus_builder.scan_debug_input",
    "normalizer.normalize_document",
    "start_active_pipeline_run", "cancel_active_pipeline_run", "run_active_pipeline", "prepare_active_corpus_source_reimport", "reset_active_corpus_db",
    "activate_release_on_existing_db", "backfill_stale", "merge_corpora", "rebuild_corpus_from_artifacts",
    "generate_embeddings",
)
L3_ADMIN_TOOLS = (
    "mcp_server.read_surface", "mcp_server.validate_surface",
    "read_owner_bundle", "read_owner_surface", "validate_owner_surface", "write_owner_surface",
    "optimizer.validate_surface", "optimizer.write_surface",
    "interpreter.validate_surface", "interpreter.write_surface",
    "corpus_builder.validate_surface", "corpus_builder.write_surface",
    "validator.validate_surface", "validator.write_surface",
    "read_runtime_settings", "write_runtime_settings", "reset_runtime_settings",
    "inspect_runtime_credentials", "set_runtime_api_key", "delete_runtime_api_key", "reveal_secret",
)

DEFAULT_POLICY: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "enabled": True,
    "default_agent_level": "L1_AUTHOR",
    "maximum_agent_level": "L3_ADMIN",
    "agent_level_env_var": "VISION_MCP_AGENT_LEVEL",
    "reject_unclassified_tools": True,
    "level_order": list(LEVEL_ORDER),
    "agent_levels": {
        "L0_READONLY": {"label": "Read-only", "description": "Inspect pipeline state, owner surface descriptors, and run read-only corpus diagnostics.", "inherits": [], "tools": list(L0_READONLY_TOOLS)},
        "L1_AUTHOR": {"label": "Author", "description": "Create exported authoring artifacts and run safe authoring checks without switching runtime corpus state.", "inherits": ["L0_READONLY"], "tools": list(L1_AUTHOR_TOOLS)},
        "L2_OPERATOR": {"label": "Operator", "description": "Run release activation, corpus context, rebuild, merge, reset, embedding, and workspace-local glossary operations.", "inherits": ["L1_AUTHOR"], "tools": list(L2_OPERATOR_TOOLS)},
        "L3_ADMIN": {"label": "Admin", "description": "Manage owner surface writes, runtime settings, credentials, and audited secret reveal.", "inherits": ["L2_OPERATOR"], "tools": list(L3_ADMIN_TOOLS)},
    },
}

__all__ = [name for name in globals() if name.isupper()]
