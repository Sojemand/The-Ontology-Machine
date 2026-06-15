from __future__ import annotations

import ast
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2]
PHASE6_FILES = (
    MODULE_ROOT / "semantic_control_kernel" / "services" / "user_interaction_service.py",
    MODULE_ROOT / "semantic_control_kernel" / "services" / "kernel_mirror_event_service.py",
    MODULE_ROOT / "semantic_control_kernel" / "services" / "client_frontend_event_sink.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "user_interaction.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "client_frontend_events.py",
    MODULE_ROOT / "semantic_control_kernel" / "surface" / "client_frontend_bridge.py",
)


def test_phase6_services_do_not_import_agent_prompt_modules() -> None:
    forbidden_fragments = ("pipeline_agent", "prompt", "chat_workflow", "kernel_client")
    for path in PHASE6_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
        assert not any(fragment in module for module in imported_modules for fragment in forbidden_fragments), path


def test_phase6_services_do_not_collect_values_through_chat_or_tool_arguments() -> None:
    forbidden_calls = {"input"}
    forbidden_names = {
        "agent_tool_arguments",
        "tool_arguments",
        "target_action_id",
        "action_token",
        "workflow_family_id",
    }
    for path in PHASE6_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls, path
            if isinstance(node, ast.Name):
                assert node.id not in forbidden_names, path
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert "ask the agent" not in node.value.casefold(), path
