from __future__ import annotations

from semantic_control_kernel.adapters.capabilities import FALSE_FRIEND_TOOL_NAMES, INVALID_KERNEL_NAME_CANDIDATES
from semantic_control_kernel.adapters.registry import AdapterRegistry, CANONICAL_FUNCTION_ADAPTER_MAP


def test_false_friend_mcp_tools_are_listed() -> None:
    assert set(FALSE_FRIEND_TOOL_NAMES) == {
        "inspect_active_corpus",
        "activation_preflight",
        "semantic_audit",
        "activate_release_on_existing_db",
        "merge_corpora",
        "rebuild_corpus_from_artifacts",
    }


def test_invalid_or_deprecated_names_are_not_exported_by_adapter_registry() -> None:
    exported = set(AdapterRegistry.exported_names())

    for name in INVALID_KERNEL_NAME_CANDIDATES:
        assert name not in CANONICAL_FUNCTION_ADAPTER_MAP
        assert name not in exported


def test_inspect_active_corpus_cannot_satisfy_kernel_state_resolver() -> None:
    assert not AdapterRegistry.can_satisfy_kernel_state_resolver("inspect_active_corpus")
    assert AdapterRegistry.can_satisfy_kernel_state_resolver("kernel_status")
