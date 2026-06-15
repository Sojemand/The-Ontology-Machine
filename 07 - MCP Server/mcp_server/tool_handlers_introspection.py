from __future__ import annotations

from .tool_handler_deps import *

_INSPECTED_MODULES = ("orchestrator", "optimizer", "interpreter", "validator", "normalizer", "corpus_builder")


def inspect_pipeline_contract_governance(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "inspect_pipeline_contract_governance")
    modules: dict[str, Any] = {}
    for key in _INSPECTED_MODULES:
        spec = module_spec(key)
        ignored = tuple(action for action in IGNORED_MANIFEST_ACTIONS.get(key, ()) if action in spec.actions)
        modules[key] = {
            "display_name": spec.display_name,
            "contract_module": spec.contract_module,
            "runtime_python": str(spec.python_executable),
            "manifest_action_count": len(spec.actions),
            "mcp_allowed_product_action_count": len(PRODUCT_ACTIONS.get(key, ())),
            "ignored_manifest_action_count": len(ignored),
            "manifest_actions": list(spec.actions),
            "mcp_allowed_product_actions": list(PRODUCT_ACTIONS.get(key, ())),
            "ignored_manifest_actions": list(ignored),
        }
    return {
        "status": "ok",
        "server_mode": "local_desktop_stdio_only",
        "pipeline_root": str(pipeline_root()),
        "known_owner_modules": list(_INSPECTED_MODULES),
        "modules": modules,
        "edit_contract_modules": {key: endpoint.contract_module for key, endpoint in EDIT_ENDPOINTS.items()},
        "admin_contract_modules": {key: endpoint.contract_module for key, endpoint in ADMIN_ENDPOINTS.items()},
        "next_tools": {
            "agent_permissions": "inspect_agent_permissions",
            "support_monitor": "inspect_support_monitor_summary",
            "active_workspace_status": "inspect_active_workspace_status",
            "active_run_status": "inspect_active_pipeline_run",
            "runtime_health": "inspect_runtime",
            "active_corpus_status": "inspect_active_corpus",
            "support_assessment": "assess_support_incident",
        },
        "governance_note": (
            "MCP delegates only to owner-local contracts. Raw state writes, UI automation, "
            "runtime admin, credential admin, L3 source debug escape hatches, and secret reveal require manifest-listed owner surfaces."
        ),
    }


def inspect_agent_permissions(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "inspect_agent_permissions")
    return {
        "status": "ok",
        "server_mode": "local_desktop_stdio_only",
        "agent_permissions": permission_summary(),
    }


def inspect_support_monitor_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    _reject_arguments(arguments, "inspect_support_monitor_summary")
    return {
        "status": "ok",
        "server_mode": "local_desktop_stdio_only",
        "support_monitor": support_monitor.support_summary_value(),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
