"""Agent-facing visibility boundary for Kernel-owned MCP syscalls."""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from .semantic_control_kernel_visibility import semantic_control_kernel_name_set, tool_visibility as semantic_control_kernel_tool_visibility


_KERNEL_SYSCALL_CONTEXT = ContextVar("kernel_syscall_context", default=False)
_HIDDEN_EXPOSURES = {"event_scoped", "kernel_internal", "kernel_continuation_scoped", "host_only_client_bridge", "legacy_hidden"}


@contextmanager
def kernel_syscall_context() -> Iterator[None]:
    token = _KERNEL_SYSCALL_CONTEXT.set(True)
    try:
        yield
    finally:
        _KERNEL_SYSCALL_CONTEXT.reset(token)


def kernel_syscall_context_active() -> bool:
    return bool(_KERNEL_SYSCALL_CONTEXT.get())


def is_known_tool(tool_name: str) -> bool:
    return _clean(tool_name) in _known_tool_names()


def is_kernel_internal_syscall(tool_name: str) -> bool:
    return tool_visibility(tool_name) in _HIDDEN_EXPOSURES


def is_externally_visible_tool(tool_name: str, known_tool_names: AbstractSet[str] | None = None) -> bool:
    return tool_visibility(tool_name, known_tool_names=known_tool_names) == "agent_visible"


def externally_visible_tool_definitions(definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known_names = frozenset(str(tool.get("name") or "").strip() for tool in definitions if str(tool.get("name") or "").strip())
    return [tool for tool in definitions if is_externally_visible_tool(str(tool.get("name") or ""), known_names)]


def external_call_block_message(tool_name: str) -> str:
    name = _clean(tool_name)
    if kernel_syscall_context_active() or not is_kernel_internal_syscall(name):
        return ""
    return (
        f"{name} ist kein direkter Agent-Einstieg im Semantic Control Kernel. "
        "Nutze die kanonischen Semantic Control Kernel Workflow-Namen."
    )


def tool_visibility(tool_name: str, *, known_tool_names: AbstractSet[str] | None = None) -> str:
    name = _clean(tool_name)
    if not name:
        return "unknown"
    semantic_visibility = semantic_control_kernel_tool_visibility(name)
    if semantic_visibility != "unknown":
        return semantic_visibility
    if known_tool_names is not None:
        return "agent_visible" if name in known_tool_names else "unknown"
    if name in _known_tool_names():
        return "agent_visible"
    return "unknown"


def _known_tool_names() -> frozenset[str]:
    from .tool_catalog import tool_names

    return tool_names()


def _clean(value: str) -> str:
    return str(value or "").strip()


__all__ = [
    "external_call_block_message",
    "externally_visible_tool_definitions",
    "is_externally_visible_tool",
    "is_kernel_internal_syscall",
    "is_known_tool",
    "kernel_syscall_context",
    "kernel_syscall_context_active",
    "tool_visibility",
]
