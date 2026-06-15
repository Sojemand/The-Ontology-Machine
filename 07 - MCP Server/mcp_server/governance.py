"""Governance constants for the Vision Pipeline MCP server.

The allow-lists here mirror SPEC_MCP_Server.md and SPEC_MCP_Workflow.md.
Actions are allowed only after the owning module exposes a manifest-listed
contract action with tests and module-local documentation.
"""

from __future__ import annotations

from .contract_client import ContractEndpoint

PRODUCT_ACTIONS: dict[str, tuple[str, ...]] = {
    "orchestrator": (
        "run",
        "reset",
        "reset_pipeline_logs",
        "embeddings",
        "activate_corpus_context",
        "inspect_source_document_sample",
        "healthcheck",
    ),
    "optimizer": (
        "classify_document",
        "extract_document",
        "healthcheck",
        "scan_debug_input",
    ),
    "interpreter": (
        "interpret_document",
        "healthcheck",
    ),
    "validator": (
        "validate_document",
        "healthcheck",
    ),
    "normalizer": (
        "normalize_document",
        "build_projection_catalog",
        "build_runtime_semantic_assets",
        "publish_semantic_release",
        "list_default_blueprints",
        "export_default_blueprint_release",
        "healthcheck",
        "debug_run",
    ),
    "corpus_builder": (
        "load_document",
        "activate_semantic_release",
        "activate_corpus_context",
        "create_empty_corpus_db",
        "reset_active_corpus_db",
        "activation_preflight",
        "generate_embeddings",
        "healthcheck",
        "scan_debug_input",
        "debug_run",
        "semantic_status",
        "read_active_semantic_release",
        "load_semantic_release",
        "semantic_audit",
        "backfill_stale",
        "merge_preflight",
        "merge_corpus_databases",
        "search",
        "stats",
        "export",
        "preview_rebuild_from_artifacts",
        "rebuild_from_artifacts",
    ),
}

OWNER_EDIT_ACTIONS = (
    "describe_surfaces",
    "read_bundle",
    "read_surface",
    "validate_surface",
    "write_surface",
)

NORMALIZER_SOURCE_ACTIONS = (
    "create_release_package",
    "read_release_package",
    "read_translation_glossary_locale",
    "list_projections",
    "read_projection",
    "list_default_blueprints",
    "derive_working_release_from_blueprint",
    "create_minimal_custom_release",
    "create_projection_draft",
    "create_locale_scaffold",
    "generate_locale_translation_payload",
    "translate_release_locale",
    "preview_impact",
    "review_bootstrap_release",
    "bootstrap_release_package",
    "review_data_informed_release",
    "refine_release_package",
    "validate_release_package",
    "compile_release_package",
    "export_semantic_release",
    "activate_semantic_release",
)

EDIT_ENDPOINTS: dict[str, ContractEndpoint] = {
    "orchestrator": ContractEndpoint(
        module_key="orchestrator",
        contract_module="orchestrator.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS,
    ),
    "optimizer": ContractEndpoint(
        module_key="optimizer",
        contract_module="ingestion_layer_vision.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS,
    ),
    "interpreter": ContractEndpoint(
        module_key="interpreter",
        contract_module="llm_interpreter.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS,
    ),
    "normalizer": ContractEndpoint(
        module_key="normalizer",
        contract_module="normalizer_vision.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS + NORMALIZER_SOURCE_ACTIONS,
    ),
    "validator": ContractEndpoint(
        module_key="validator",
        contract_module="validator_vision.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS,
    ),
    "corpus_builder": ContractEndpoint(
        module_key="corpus_builder",
        contract_module="corpus_builder.edit_contract",
        allowed_actions=OWNER_EDIT_ACTIONS,
    ),
}

ADMIN_ACTIONS = (
    "inspect_runtime",
    "manage_runtime_settings",
    "manage_credentials",
    "reveal_secret",
)

ADMIN_ENDPOINTS: dict[str, ContractEndpoint] = {
    "orchestrator": ContractEndpoint(
        module_key="orchestrator",
        contract_module="orchestrator.admin_contract",
        allowed_actions=ADMIN_ACTIONS,
        check_manifest_actions=True,
        manifest_actions_key="admin_actions",
    ),
}

IGNORED_MANIFEST_ACTIONS: dict[str, tuple[str, ...]] = {}
