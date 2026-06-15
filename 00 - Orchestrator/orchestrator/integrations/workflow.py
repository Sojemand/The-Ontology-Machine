"""Workflow orchestration for sibling-module contract calls."""

from __future__ import annotations

from pathlib import Path

from ..bootstrap import resolve_module_runtime
from ..models.types import RuntimeSettingsState
from . import adapter, registry
from .workflow_actions import SubmodulePipelineModulesActions
from .workflow_downstream_actions import SubmodulePipelineModulesDownstreamActions


class SubmodulePipelineModules(SubmodulePipelineModulesActions, SubmodulePipelineModulesDownstreamActions):
    """Thin workflow surface over subprocess-based sibling-module contracts."""

    def __init__(self, state_dir: Path | None = None) -> None:
        required_actions = registry.required_actions_by_module()
        self._runtime_specs = {
            key: resolve_module_runtime(key, required_actions=required_actions[key])
            for key in registry.default_module_keys()
        }
        self._state_dir = Path(state_dir) if state_dir is not None else None
        if self._state_dir is not None:
            from ..state import load_runtime_settings

            self._runtime_settings = load_runtime_settings(self._state_dir)
        else:
            self._runtime_settings = RuntimeSettingsState()
