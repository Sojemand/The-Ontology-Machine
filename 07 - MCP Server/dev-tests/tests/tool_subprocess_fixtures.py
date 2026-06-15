from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from mcp_server import contract_client, support_monitor, tool_handlers
from mcp_server.contract_client import ModuleSpec

from tests.tool_subprocess_catalog import OFFLINE_SUBPROCESS_TOOLS, GATED_SUBPROCESS_TOOLS
from tests.tool_subprocess_helpers import _copy_regression_artifacts, _write_empty_sqlite

_REAL_MODULE_SPEC = contract_client.module_spec


@pytest.fixture(autouse=True)
def isolated_support_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(support_monitor, "state_root", lambda: tmp_path / "mcp_support")


@pytest.fixture()
def isolated_owner_specs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, ModuleSpec]:
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    specs: dict[str, ModuleSpec] = {}
    owners_root = tmp_path / "owners"
    owners_root.mkdir()
    monkeypatch.setenv("INTERPRETER_HOME", str(tmp_path / "interpreter-home"))
    for module_key in ("orchestrator", "interpreter", "validator", "normalizer", "corpus_builder"):
        real = _REAL_MODULE_SPEC(module_key)
        copied_root = owners_root / real.root.name
        shutil.copytree(real.root, copied_root, ignore=_owner_copy_ignore(real.root))
        specs[module_key] = ModuleSpec(
            key=real.key,
            root=copied_root,
            display_name=real.display_name,
            contract_module=real.contract_module,
            runtime_dir=real.runtime_dir,
            python_executable=real.python_executable,
            actions=real.actions,
            manifest_actions=real.manifest_actions,
        )
    optimizer = _REAL_MODULE_SPEC("optimizer")
    specs["optimizer"] = ModuleSpec(
        key=optimizer.key,
        root=optimizer.root,
        display_name=optimizer.display_name,
        contract_module=optimizer.contract_module,
        runtime_dir=optimizer.runtime_dir,
        python_executable=optimizer.python_executable,
        actions=optimizer.actions,
        manifest_actions=optimizer.manifest_actions,
    )

    def fake_module_spec(module_key: str) -> ModuleSpec:
        return specs[module_key]

    monkeypatch.setattr(contract_client, "module_spec", fake_module_spec)
    monkeypatch.setattr(tool_handlers, "module_spec", fake_module_spec)
    return specs


def _owner_copy_ignore(root: Path):
    root = Path(root).resolve()

    def ignore(current: str, names: list[str]) -> set[str]:
        current_path = Path(current).resolve()
        try:
            relative = current_path.relative_to(root)
        except ValueError:
            relative = Path()
        ignored = {
            name
            for name in names
            if name == "__pycache__"
            or name.startswith("pytest-cache-files-")
            or name.startswith("pytest-tmp-")
            or name.startswith(".tmp")
            or name in {".pytest_cache", ".pytest-basetemp-full", ".pytest-tmp"}
        }
        if relative == Path("."):
            ignored.update({"runtime", "dev-tests", "dist", "installer", "state", "output"})
        return ignored

    return ignore


@pytest.fixture()
def integration_paths(tmp_path: Path) -> dict[str, str]:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    releases = tmp_path / "releases"
    releases.mkdir()
    confirmations = tmp_path / "confirmations"
    confirmations.mkdir()
    artifacts = tmp_path / "artifacts"
    _copy_regression_artifacts(artifacts)
    active_db = corpus_root / "active.db"
    source_db = corpus_root / "source.db"
    target_db = corpus_root / "target.db"
    for db_path in (active_db, source_db, target_db):
        _write_empty_sqlite(db_path)
    return {
        "corpus_root": str(corpus_root),
        "active_db": str(active_db),
        "fresh_db": str(corpus_root / "fresh.db"),
        "blueprint_db": str(corpus_root / "blueprint.db"),
        "release_db": str(corpus_root / "release-created.db"),
        "source_db": str(source_db),
        "target_db": str(target_db),
        "release_path": str(releases / "default.semantic_release.json"),
        "working_release_path": str(releases / "working.semantic_release.json"),
        "export_path": str(tmp_path / "exports" / "corpus.jsonl"),
        "confirmation_dir": str(confirmations),
        "artifact_root": str(artifacts),
        "workspace_artifact_root": str(tmp_path / "workspace-artifacts"),
    }


__all__ = ["OFFLINE_SUBPROCESS_TOOLS", "GATED_SUBPROCESS_TOOLS", "isolated_support_root", "isolated_owner_specs", "integration_paths"]
