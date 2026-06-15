from __future__ import annotations

import re

from semantic_control_kernel.surface.agent_tools import list_permanent_tools


FORBIDDEN_MODEL_VISIBLE_TERMS = (
    "arguments",
    "parameters",
    "payload",
    "precondition",
    "confirmation",
    "blocker",
    "workflow_family",
    "permission_level",
    "action_token",
    "pipeline_action",
    "adapter",
    "mcp handler",
)


def test_tool_descriptions_avoid_argument_and_implementation_language() -> None:
    for definition in list_permanent_tools():
        for field_name in ("description", "outcome", "does_not"):
            value = str(definition.to_dict()[field_name]).lower()
            for term in FORBIDDEN_MODEL_VISIBLE_TERMS:
                assert term not in value, f"{definition.tool_name}.{field_name} contains {term}"


def test_tool_descriptions_are_compact_english_product_language() -> None:
    for definition in list_permanent_tools():
        payload = definition.to_dict()
        assert re.match(r"^[A-Z0-9]", payload["description"])
        assert payload["description"].endswith(".")
        assert len(payload["description"].split()) <= 18
        assert not payload["description"].startswith(("Calls ", "Runs the handler", "Executes adapter"))


def test_pipeline_terms_appear_only_where_they_help_routing() -> None:
    pipeline_tools = {
        "manual_pipeline_run",
        "kernel_status",
        "kernel_cancel_active_run",
    }

    for definition in list_permanent_tools():
        mentions_pipeline = "Pipeline" in definition.description or "Pipeline" in definition.outcome
        if mentions_pipeline:
            assert definition.tool_name in pipeline_tools
