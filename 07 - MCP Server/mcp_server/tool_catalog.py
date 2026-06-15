"""MCP tool catalog for the local Vision Pipeline control plane."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

from .tool_catalog_artifacts import artifact_tools
from .tool_catalog_corpus_edit import corpus_edit_tools
from .tool_catalog_core import core_tools
from .tool_catalog_interpreter import interpreter_tools
from .tool_catalog_normalizer import normalizer_tools
from .tool_catalog_optimizer import optimizer_tools
from .tool_catalog_pipeline import pipeline_tools
from .tool_catalog_runtime import runtime_tools
from .tool_catalog_semantic import semantic_tools
from .tool_catalog_semantic_control_kernel import (
    clear_semantic_control_kernel_tool_cache,
    semantic_control_kernel_catalog_cache_token,
    semantic_control_kernel_tools,
)
from .tool_catalog_validator import validator_tools
from .tool_catalog_working_release import working_release_tools
from .tool_catalog_workspace import workspace_tools

_TOOL_GROUPS = (
    core_tools,
    optimizer_tools,
    interpreter_tools,
    validator_tools,
    normalizer_tools,
    working_release_tools,
    workspace_tools,
    pipeline_tools,
    semantic_tools,
    corpus_edit_tools,
    artifact_tools,
    runtime_tools,
    semantic_control_kernel_tools,
)


def tool_definitions() -> list[dict[str, Any]]:
    return [deepcopy(tool) for tool in _tool_definition_snapshot(catalog_cache_token())]


def tool_names() -> frozenset[str]:
    return _tool_name_snapshot(catalog_cache_token())


def catalog_cache_token() -> tuple[object, ...]:
    return (
        *(id(group) for group in _TOOL_GROUPS),
        semantic_control_kernel_catalog_cache_token(),
    )


def clear_tool_catalog_cache() -> None:
    _tool_definition_snapshot.cache_clear()
    _tool_name_snapshot.cache_clear()
    clear_semantic_control_kernel_tool_cache()


@lru_cache(maxsize=8)
def _tool_definition_snapshot(cache_token: tuple[object, ...]) -> tuple[dict[str, Any], ...]:
    tools: list[dict[str, Any]] = []
    for group in _TOOL_GROUPS:
        tools.extend(group())
    return tuple(tools)


@lru_cache(maxsize=8)
def _tool_name_snapshot(cache_token: tuple[object, ...]) -> frozenset[str]:
    return frozenset(str(tool.get("name") or "").strip() for tool in _tool_definition_snapshot(cache_token) if str(tool.get("name") or "").strip())


def _tool_groups():
    return _TOOL_GROUPS
