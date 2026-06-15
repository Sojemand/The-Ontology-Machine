from __future__ import annotations
from functools import lru_cache
from typing import Any
from .tool_handler_types import ToolFailure, ToolHandler
from . import tool_handler_contracts as _contracts
from . import tool_handler_pipeline_context as _pipeline_context
from . import tool_handler_pipeline_snapshot as _pipeline_snapshot
from . import tool_handler_pipeline_store as _pipeline_store
from . import tool_handlers_artifact_rebuild as _artifact_rebuild
from . import tool_handlers_authoring_custom as _authoring_custom
from . import tool_handlers_authoring_readiness as _authoring_readiness
from . import tool_handlers_corpus_builder_pipeline as _corpus_pipeline
from . import tool_handlers_corpus_context as _corpus_context
from . import tool_handlers_corpus_edit as _corpus_edit
from . import tool_handlers_corpus_query as _corpus_query
from . import tool_handlers_extraction as _extraction
from . import tool_handlers_glossary as _glossary
from . import tool_handlers_introspection as _introspection
from . import tool_handlers_interpreter as _interpreter
from . import tool_handlers_mcp_server as _mcp_server
from . import tool_handlers_normalizer as _normalizer
from . import tool_handlers_optimizer as _optimizer
from . import tool_handlers_owner_edit as _owner_edit
from . import tool_handlers_orchestrator as _orchestrator
from . import tool_handler_corpus_reimport_apply as _corpus_reimport_apply
from . import tool_handler_corpus_reimport_paths as _corpus_reimport_paths
from . import tool_handlers_corpus_reimport as _corpus_reimport
from . import tool_handlers_pipeline_run as _pipeline_run
from . import tool_handlers_pipeline_status as _pipeline_status, tool_handlers_product_advisory as _product_advisory
from . import tool_handlers_workspace_status as _workspace_status
from . import tool_handlers_release_revision as _release_revision
from . import tool_handler_release_revision_db as _release_revision_db
from . import tool_handlers_runtime_admin as _runtime_admin
from . import tool_handlers_semantic_control_kernel as _semantic_control_kernel
from . import tool_handlers_semantic_release as _semantic_release
from . import tool_handler_source_fit_context as _source_fit_context
from . import tool_handler_source_sample_set_review as _source_sample_set_review
from . import tool_handlers_source_fit as _source_fit
from . import tool_handlers_source_sample_set as _source_sample_set
from . import tool_handlers_support as _support
from . import tool_handlers_validator as _validator
from . import tool_handlers_validator_edit as _validator_edit
from . import tool_handlers_working_release as _working_release
from . import tool_handlers_workspace as _workspace
from . import tool_handlers_workspace_release as _workspace_release
from . import tool_handlers_workspace_reset as _workspace_reset

_HOOK_MODULES = (
    _contracts, _pipeline_context, _pipeline_snapshot, _pipeline_store, _artifact_rebuild,
    _authoring_custom, _authoring_readiness, _corpus_pipeline, _corpus_context, _corpus_edit,
    _corpus_query, _extraction, _glossary, _introspection, _interpreter, _mcp_server, _normalizer,
    _optimizer, _owner_edit, _orchestrator, _corpus_reimport_apply, _corpus_reimport_paths,
    _corpus_reimport, _pipeline_run, _pipeline_status,
    _workspace_status, _release_revision, _release_revision_db, _runtime_admin,
    _semantic_release, _source_fit_context, _source_sample_set_review, _source_fit, _source_sample_set, _support, _validator, _validator_edit, _working_release, _workspace,
    _workspace_release, _workspace_reset,
)
_PATCHABLE_NAMES = ("_invoke_product", "_invoke_edit", "_invoke_admin", "module_spec", "_pipeline_runs_dir", "_orchestrator_ui_state_path")
_HANDLER_SPECS = (
    ("mcp_server.describe_surfaces", _mcp_server, "mcp_server_describe_surfaces"),
    ("mcp_server.read_surface", _mcp_server, "mcp_server_read_surface"),
    ("mcp_server.validate_surface", _mcp_server, "mcp_server_validate_surface"),
    ("mcp_server.healthcheck", _mcp_server, "mcp_server_healthcheck"),
    ("inspect_pipeline_contract_governance", _introspection, "inspect_pipeline_contract_governance"),
    ("inspect_agent_permissions", _introspection, "inspect_agent_permissions"),
    ("inspect_support_monitor_summary", _introspection, "inspect_support_monitor_summary"),
    *((name, _product_advisory, name) for name in ("inspect_pipeline_product_context", "explain_pipeline_capabilities", "recommend_pipeline_next_steps")),
    ("optimizer.classify_document", _optimizer, "optimizer_classify_document"),
    ("optimizer.extract_document", _optimizer, "optimizer_extract_document"),
    ("optimizer.healthcheck", _optimizer, "optimizer_healthcheck"),
    ("optimizer.scan_debug_input", _optimizer, "optimizer_scan_debug_input"),
    ("optimizer.describe_surfaces", _optimizer, "optimizer_describe_surfaces"),
    ("optimizer.read_surface", _optimizer, "optimizer_read_surface"),
    ("optimizer.validate_surface", _optimizer, "optimizer_validate_surface"),
    ("optimizer.write_surface", _optimizer, "optimizer_write_surface"),
    ("interpreter.interpret_document", _interpreter, "interpreter_interpret_document"),
    ("interpreter.healthcheck", _interpreter, "interpreter_healthcheck"),
    ("interpreter.describe_surfaces", _interpreter, "interpreter_describe_surfaces"),
    ("interpreter.read_surface", _interpreter, "interpreter_read_surface"),
    ("interpreter.validate_surface", _interpreter, "interpreter_validate_surface"),
    ("interpreter.write_surface", _interpreter, "interpreter_write_surface"),
    ("validator.validate_document", _validator, "validator_validate_document"),
    ("validator.healthcheck", _validator, "validator_healthcheck"),
    ("validator.describe_surfaces", _validator_edit, "validator_describe_surfaces"),
    ("validator.read_surface", _validator_edit, "validator_read_surface"),
    ("validator.validate_surface", _validator_edit, "validator_validate_surface"),
    ("validator.write_surface", _validator_edit, "validator_write_surface"),
    ("normalizer.normalize_document", _normalizer, "normalizer_normalize_document"),
    ("normalizer.healthcheck", _normalizer, "normalizer_healthcheck"),
    ("assess_support_incident", _support, "assess_support_incident"),
    ("list_support_incidents", _support, "list_support_incidents"),
    ("preview_support_bug_report", _support, "preview_support_bug_report"),
    ("build_support_bug_report", _support, "build_support_bug_report"),
    ("queue_support_bug_report", _support, "queue_support_bug_report"),
    ("dismiss_support_incident", _support, "dismiss_support_incident"),
    ("describe_owner_surfaces", _owner_edit, "describe_owner_surfaces"),
    ("read_owner_bundle", _owner_edit, "read_owner_bundle"),
    ("read_owner_surface", _owner_edit, "read_owner_surface"),
    ("validate_owner_surface", _owner_edit, "validate_owner_surface"),
    ("write_owner_surface", _owner_edit, "write_owner_surface"),
    ("orchestrator.healthcheck", _orchestrator, "orchestrator_healthcheck"),
    ("orchestrator.reset", _orchestrator, "orchestrator_reset"),
    ("list_default_blueprints", _extraction, "list_default_blueprints"),
    ("inspect_source_document_sample", _extraction, "inspect_source_document_sample"),
    ("export_default_blueprint_release", _extraction, "export_default_blueprint_release"),
    ("read_working_release", _working_release, "read_working_release"),
    ("list_working_release_profiles", _working_release, "list_working_release_profiles"),
    ("read_working_release_profile", _working_release, "read_working_release_profile"),
    ("validate_working_release", _working_release, "validate_working_release"),
    ("compile_working_release", _working_release, "compile_working_release"),
    ("preview_working_release_impact", _working_release, "preview_working_release_impact"),
    ("create_working_release_package", _working_release, "create_working_release_package"),
    ("review_bootstrap_release", _working_release, "review_bootstrap_release"),
    ("apply_bootstrap_release", _working_release, "apply_bootstrap_release"),
    ("review_data_informed_release", _working_release, "review_data_informed_release"),
    ("refine_working_release_from_sample", _working_release, "refine_working_release_from_sample"),
    ("export_working_release", _working_release, "export_working_release"),
    ("derive_working_release_from_blueprint", _authoring_custom, "derive_working_release_from_blueprint"),
    ("create_locale_scaffold", _authoring_readiness, "create_locale_scaffold"),
    ("create_minimal_custom_release", _authoring_custom, "create_minimal_custom_release"),
    ("create_projection_draft", _authoring_custom, "create_projection_draft"),
    ("generate_locale_translation_payload", _authoring_custom, "generate_locale_translation_payload"),
    ("translate_working_release_locale", _authoring_custom, "translate_working_release_locale"),
    ("read_translation_glossary", _glossary, "read_translation_glossary"),
    ("upsert_translation_glossary_entry", _glossary, "upsert_translation_glossary_entry"),
    ("remove_translation_glossary_entry", _glossary, "remove_translation_glossary_entry"),
    ("corpus_builder.load_document", _corpus_pipeline, "corpus_builder_load_document"),
    ("corpus_builder.healthcheck", _corpus_pipeline, "corpus_builder_healthcheck"),
    ("corpus_builder.scan_debug_input", _corpus_pipeline, "corpus_builder_scan_debug_input"),
    ("corpus_builder.describe_surfaces", _corpus_edit, "corpus_builder_describe_surfaces"),
    ("corpus_builder.read_surface", _corpus_edit, "corpus_builder_read_surface"),
    ("corpus_builder.validate_surface", _corpus_edit, "corpus_builder_validate_surface"),
    ("corpus_builder.write_surface", _corpus_edit, "corpus_builder_write_surface"),
    ("inspect_active_corpus", _corpus_context, "inspect_active_corpus"),
    ("activate_corpus_context", _corpus_context, "activate_corpus_context"),
    ("create_empty_corpus_db", _corpus_context, "create_empty_corpus_db"),
    ("prepare_pipeline_workspace_root", _workspace, "prepare_pipeline_workspace_root"),
    ("write_workspace_release_change_confirmation", _workspace_release, "write_workspace_release_change_confirmation"),
    ("write_workspace_db_reset_confirmation", _workspace_reset, "write_workspace_db_reset_confirmation"),
    ("verify_workspace_active_release", _workspace_release, "verify_workspace_active_release"),
    ("read_revision_candidate_release", _release_revision, "read_revision_candidate_release"),
    ("inspect_release_revision_context", _release_revision, "inspect_release_revision_context"),
    ("classify_release_revision", _release_revision, "classify_release_revision"),
    ("inspect_active_workspace_status", _workspace_status, "inspect_active_workspace_status"),
    ("inspect_current_environment_status", _workspace_status, "inspect_current_environment_status"),
    ("run_active_pipeline", _pipeline_run, "run_active_pipeline"),
    ("start_active_pipeline_run", _pipeline_run, "start_active_pipeline_run"),
    ("inspect_active_pipeline_run", _pipeline_status, "inspect_active_pipeline_run"),
    ("cancel_active_pipeline_run", _pipeline_status, "cancel_active_pipeline_run"),
    ("preview_active_corpus_source_reimport", _corpus_reimport, "preview_active_corpus_source_reimport"),
    ("prepare_active_corpus_source_reimport", _corpus_reimport, "prepare_active_corpus_source_reimport"),
    ("assess_source_document_fit", _source_fit, "assess_source_document_fit"),
    ("review_source_document_taxonomy_coverage", _source_fit, "review_source_document_taxonomy_coverage"),
    ("review_source_sample_set_taxonomy_coverage", _source_sample_set, "review_source_sample_set_taxonomy_coverage"),
    ("prepare_source_samples_for_input", _source_sample_set, "prepare_source_samples_for_input"),
    ("read_active_semantic_release", _semantic_release, "read_active_semantic_release"),
    ("reset_active_corpus_db", _semantic_release, "reset_active_corpus_db"),
    ("load_semantic_release", _semantic_release, "load_semantic_release"),
    ("semantic_audit", _semantic_release, "semantic_audit"),
    ("activation_preflight", _semantic_release, "activation_preflight"),
    ("activate_release_on_existing_db", _semantic_release, "activate_release_on_existing_db"),
    ("backfill_stale", _semantic_release, "backfill_stale"),
    ("merge_preflight", _semantic_release, "merge_preflight"),
    ("merge_corpora", _semantic_release, "merge_corpora"),
    ("preview_rebuild_from_artifacts", _artifact_rebuild, "preview_rebuild_from_artifacts"),
    ("rebuild_corpus_from_artifacts", _artifact_rebuild, "rebuild_corpus_from_artifacts"),
    ("generate_embeddings", _corpus_query, "generate_embeddings"),
    ("search_corpus", _corpus_query, "search_corpus"),
    ("corpus_stats", _corpus_query, "corpus_stats"),
    ("export_corpus", _corpus_query, "export_corpus"),
    ("inspect_runtime", _runtime_admin, "inspect_runtime"),
    ("read_runtime_settings", _runtime_admin, "read_runtime_settings"),
    ("write_runtime_settings", _runtime_admin, "write_runtime_settings"),
    ("reset_runtime_settings", _runtime_admin, "reset_runtime_settings"),
    ("inspect_runtime_credentials", _runtime_admin, "inspect_runtime_credentials"),
    ("set_runtime_api_key", _runtime_admin, "set_runtime_api_key"),
    ("delete_runtime_api_key", _runtime_admin, "delete_runtime_api_key"),
    ("reveal_secret", _runtime_admin, "reveal_secret"),
    *((name, _semantic_control_kernel, name) for name in _semantic_control_kernel.SEMANTIC_CONTROL_KERNEL_HANDLER_NAMES),
)
def sync_patchable_hooks(current: dict[str, Any]) -> None:
    for module in _HOOK_MODULES:
        for name in _PATCHABLE_NAMES:
            if hasattr(module, name):
                setattr(module, name, current[name])

def handlers() -> dict[str, ToolHandler]:
    return _cached_handlers()
@lru_cache(maxsize=1)
def _cached_handlers() -> dict[str, ToolHandler]:
    return {name: _handler_attr(module, attr, name) for name, module, attr in _HANDLER_SPECS}
def _handler_attr(module: Any, attr: str, name: str) -> ToolHandler:
    handler = getattr(module, attr, None)
    if callable(handler):
        return handler
    def missing_handler(_arguments: dict[str, Any]) -> dict[str, Any]:
        raise ToolFailure(f"Handler fehlt fuer katalogisiertes Tool: {name}")
    return missing_handler

__all__ = ["handlers", "sync_patchable_hooks"]
