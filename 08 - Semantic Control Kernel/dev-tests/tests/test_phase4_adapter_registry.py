from __future__ import annotations

import importlib
import re
from pathlib import Path

from semantic_control_kernel.adapters.capabilities import ADAPTER_CATEGORIES
from semantic_control_kernel.adapters.registry import CANONICAL_FUNCTION_ADAPTER_MAP
from semantic_control_kernel.types.adapter_results import CAPABILITY_STATUSES


MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent
SPEC_22 = PIPELINE_ROOT / "Semantic Kernel SPEC" / "22_mcp_kernel_pipeline_function_contract.md"

ADAPTER_MODULES = (
    "semantic_control_kernel.adapters",
    "semantic_control_kernel.adapters.base",
    "semantic_control_kernel.adapters.capabilities",
    "semantic_control_kernel.adapters.errors",
    "semantic_control_kernel.adapters.invocation",
    "semantic_control_kernel.adapters.registry",
    "semantic_control_kernel.adapters.workspace",
    "semantic_control_kernel.adapters.orchestrator",
    "semantic_control_kernel.adapters.corpus",
    "semantic_control_kernel.adapters.semantic_release",
    "semantic_control_kernel.adapters.pipeline_batch",
    "semantic_control_kernel.adapters.merge",
    "semantic_control_kernel.adapters.embedding",
    "semantic_control_kernel.adapters.optimizer",
    "semantic_control_kernel.adapters.interpreter",
    "semantic_control_kernel.adapters.validator",
    "semantic_control_kernel.adapters.normalizer",
)


def _spec22_canonical_surface_names() -> set[str]:
    text = SPEC_22.read_text(encoding="utf-8")
    section = text.split("Canonical MCP-Facing Kernel Surface", 1)[1].split(
        "Workflow entry route exposure",
        1,
    )[0]
    return {
        match.group(1)
        for match in re.finditer(r"^\t- ([a-z][a-z0-9_]+)$", section, flags=re.MULTILINE)
    }


def test_drift_preflight_recorded_for_phase4() -> None:
    fixture = MODULE_ROOT / "dev-tests" / "fixtures" / "adapters" / "phase4_drift_preflight.json"
    text = fixture.read_text(encoding="utf-8")

    assert "drift_preflight: build_plan_authority_applied" in text
    assert "adapter.call_request.v1" in text
    assert "Phase 19 owner-domain actions" in text


def test_every_adapter_module_in_phase4_deliverables_is_importable() -> None:
    for module_name in ADAPTER_MODULES:
        assert importlib.import_module(module_name)


def test_registry_contains_every_spec22_canonical_kernel_surface_name() -> None:
    expected = _spec22_canonical_surface_names()

    assert expected
    assert expected <= set(CANONICAL_FUNCTION_ADAPTER_MAP)


def test_mapped_categories_and_capability_statuses_are_phase4_values() -> None:
    for function_name, mapping in CANONICAL_FUNCTION_ADAPTER_MAP.items():
        assert function_name
        assert mapping.categories
        assert mapping.methods
        assert set(mapping.categories) <= set(ADAPTER_CATEGORIES)
        assert set(mapping.capability_status) <= set(CAPABILITY_STATUSES)
