from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.integrations import SubmodulePipelineModules, required_actions_by_module
from tests.test_integrations_workflow import _runtime_spec


def test_submodule_pipeline_modules_uses_central_required_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, tuple[str, ...]]] = []

    def fake_resolve(module_key: str, *, required_actions: tuple[str, ...]):  # noqa: ANN001
        captured.append((module_key, required_actions))
        return _runtime_spec(tmp_path, module_key)

    monkeypatch.setattr("orchestrator.integrations.workflow.resolve_module_runtime", fake_resolve)

    SubmodulePipelineModules()

    assert captured == list(required_actions_by_module().items())
