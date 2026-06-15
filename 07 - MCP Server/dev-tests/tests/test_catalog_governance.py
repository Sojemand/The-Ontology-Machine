from __future__ import annotations

from mcp_server.governance import ADMIN_ACTIONS, PRODUCT_ACTIONS
from mcp_server.tools import call_tool, tool_definitions


def test_mcp_allow_list_excludes_spec_blocked_manifest_drift() -> None:
    assert tool_definitions()
    assert "create_zero_shot_working_release" not in PRODUCT_ACTIONS["normalizer"]
    assert "create_zero_shot_working_release" not in {tool["name"] for tool in tool_definitions()}
    assert "activate_corpus_context" in PRODUCT_ACTIONS["orchestrator"]
    assert "activate_corpus_context" in PRODUCT_ACTIONS["corpus_builder"]
    assert "create_empty_corpus_db" in PRODUCT_ACTIONS["corpus_builder"]
    assert "reset_active_corpus_db" in PRODUCT_ACTIONS["corpus_builder"]
    assert "manage_runtime_settings" in ADMIN_ACTIONS
    assert "manage_credentials" in ADMIN_ACTIONS
    assert "reveal_secret" in ADMIN_ACTIONS


def test_retired_normalizer_scope_tools_removed_and_atomic_package_tool_exists() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    retired = {
        "inspect_extraction_packs",
        "check_working_release_readiness",
        "broaden_custom_release",
        "normalizer_source_action",
    }
    schema = tools["create_working_release_package"]["inputSchema"]
    properties = schema["properties"]

    assert retired.isdisjoint(tools)
    assert set(properties) == {"artifact_folder", "default_runtime_locale", "projection_ids"}
    assert set(schema["required"]) == {"artifact_folder"}
    assert "action" not in properties
    assert "operation" not in properties
    assert "payload" not in properties


def test_glossary_macro_removed_and_atomic_tools_exist() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    assert "manage_translation_glossary" not in tools
    assert {"read_translation_glossary", "upsert_translation_glossary_entry", "remove_translation_glossary_entry"} <= set(tools)


def test_retired_scope_tool_replacements_are_atomic() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    package = tools["create_working_release_package"]["description"]
    assert "delegating exactly once" in package
    assert "does not validate, compile, export, activate" in package


def test_scope_macros_removed_and_atomic_tools_exist() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}
    retired = {
        "inspect_pipeline",
        "support_incident_workflow",
        "manage_runtime_settings",
        "manage_credentials",
        "inspect_extraction_packs",
        "check_working_release_readiness",
        "broaden_custom_release",
        "normalizer_source_action",
        "create_pipeline_workspace_from_working_release",
        "activate_working_release_on_workspace_db",
        "reset_workspace_db_and_activate_working_release",
        "build_and_activate_release_for_active_corpus",
        "create_new_corpus_from_release",
        "create_and_rebuild_new_corpus_db",
        "plan_custom_release_revision",
    }
    added = {
        "inspect_pipeline_contract_governance",
        "inspect_agent_permissions",
        "inspect_support_monitor_summary",
        "create_working_release_package",
        "assess_support_incident",
        "list_support_incidents",
        "preview_support_bug_report",
        "build_support_bug_report",
        "queue_support_bug_report",
        "dismiss_support_incident",
        "read_runtime_settings",
        "write_runtime_settings",
        "reset_runtime_settings",
        "inspect_runtime_credentials",
        "set_runtime_api_key",
        "delete_runtime_api_key",
        "write_workspace_release_change_confirmation",
        "write_workspace_db_reset_confirmation",
        "verify_workspace_active_release",
        "read_revision_candidate_release",
        "inspect_release_revision_context",
        "classify_release_revision",
    }

    assert retired.isdisjoint(tools)
    assert added <= set(tools)

    for name in added:
        properties = tools[name]["inputSchema"].get("properties", {})
        assert "action" not in properties
        assert "operation" not in properties
        assert not any(key.startswith("include_") for key in properties)

    rebuild_props = tools["rebuild_corpus_from_artifacts"]["inputSchema"]["properties"]
    assert "release_path" not in rebuild_props


def test_orchestrator_atom_tools_are_first_class_catalog_entries() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    assert {"orchestrator.reset", "orchestrator.healthcheck"} <= set(tools)
    for name in ("orchestrator.reset", "orchestrator.healthcheck"):
        schema = tools[name]["inputSchema"]
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["required"] == []
        assert schema["additionalProperties"] is False


def test_corpus_builder_edit_atom_tools_are_first_class_catalog_entries() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    expected = {
        "corpus_builder.describe_surfaces",
        "corpus_builder.read_surface",
        "corpus_builder.validate_surface",
        "corpus_builder.write_surface",
    }
    assert expected <= set(tools)
    assert tools["corpus_builder.describe_surfaces"]["inputSchema"]["properties"] == {}
    for name in expected - {"corpus_builder.describe_surfaces"}:
        schema = tools[name]["inputSchema"]
        assert "module" not in schema["properties"]
        assert "action" not in schema["properties"]
        assert "operation" not in schema["properties"]


def test_mcp_server_atom_tools_are_first_class_catalog_entries() -> None:
    tools = {tool["name"]: tool for tool in tool_definitions()}

    expected = {
        "mcp_server.describe_surfaces",
        "mcp_server.read_surface",
        "mcp_server.validate_surface",
        "mcp_server.healthcheck",
    }
    assert expected <= set(tools)
    assert tools["mcp_server.describe_surfaces"]["inputSchema"]["properties"] == {}
    assert set(tools["mcp_server.healthcheck"]["inputSchema"]["properties"]) == {"strict_runtime"}
    assert set(tools["mcp_server.read_surface"]["inputSchema"]["required"]) == {"surface_id"}
    assert set(tools["mcp_server.validate_surface"]["inputSchema"]["required"]) == {"surface_id", "value"}
    assert tools["mcp_server.read_surface"]["inputSchema"]["additionalProperties"] is False
    assert tools["mcp_server.validate_surface"]["inputSchema"]["additionalProperties"] is False


def test_contract_governance_introspection_reports_owner_metadata() -> None:
    result = call_tool("inspect_pipeline_contract_governance", {})

    assert result["status"] == "ok"
    assert result["server_mode"] == "local_desktop_stdio_only"
    assert result["admin_contract_modules"]["orchestrator"] == "orchestrator.admin_contract"
    assert result["modules"]["optimizer"]["contract_module"] == "ingestion_layer_vision.orchestrator_contract"
    assert "extract_document" in result["modules"]["optimizer"]["mcp_allowed_product_actions"]
    assert result["modules"]["normalizer"]["manifest_action_count"] > 0
    assert "manifest_actions" in result["modules"]["normalizer"]
    assert result["next_tools"]["active_workspace_status"] == "inspect_active_workspace_status"
    assert result["next_tools"]["active_run_status"] == "inspect_active_pipeline_run"


def test_agent_permission_introspection_is_separate() -> None:
    result = call_tool("inspect_agent_permissions", {})

    assert result["status"] == "ok"
    assert "unclassified_tools" in result["agent_permissions"]


def test_support_monitor_summary_introspection_is_separate() -> None:
    result = call_tool("inspect_support_monitor_summary", {})

    assert result["status"] == "ok"
    assert "active_incident_count" in result["support_monitor"]
    assert "recent_incidents" not in result["support_monitor"]
