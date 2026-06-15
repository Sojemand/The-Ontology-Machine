from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = PIPELINE_ROOT / "tools"


def _load_tool_module(name: str, path: Path):
    if str(TOOLS_ROOT) not in sys.path:
        sys.path.insert(0, str(TOOLS_ROOT))
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_refresh_phase0_artifacts_materializes_all_targets_and_is_idempotent(tmp_path: Path) -> None:
    module = _load_tool_module("test_refresh_phase0_artifacts_tool", TOOLS_ROOT / "refresh_phase0_artifacts.py")
    optimizer_fixture_path = tmp_path / "01 - Optimizer" / "dev-tests" / "fixtures" / "runtime_semantic_assets_v1.json"
    corpus_release_path = tmp_path / "05 - Corpus Builder" / "config" / "semantic_release.default.json"
    corpus_active_release_path = tmp_path / "05 - Corpus Builder" / "state" / "semantic_release.active.json"
    corpus_stage_release_path = tmp_path / "05 - Corpus Builder" / "dist" / "stage" / "config" / "semantic_release.default.json"

    first = module.refresh_phase0_artifacts(
        optimizer_fixture_path=optimizer_fixture_path,
        corpus_release_path=corpus_release_path,
        corpus_active_release_path=corpus_active_release_path,
        corpus_stage_release_path=corpus_stage_release_path,
    )

    assert {Path(path) for path in first["updated_paths"]} == {
        optimizer_fixture_path,
        corpus_release_path,
        corpus_active_release_path,
        corpus_stage_release_path,
    }
    module.verify_phase0_artifacts(
        optimizer_fixture_path=optimizer_fixture_path,
        corpus_release_path=corpus_release_path,
        corpus_active_release_path=corpus_active_release_path,
        corpus_stage_release_path=corpus_stage_release_path,
    )

    published_release = json.loads(corpus_release_path.read_text(encoding="utf-8"))
    assert published_release == json.loads(corpus_active_release_path.read_text(encoding="utf-8"))
    assert published_release == json.loads(corpus_stage_release_path.read_text(encoding="utf-8"))
    assert json.loads(optimizer_fixture_path.read_text(encoding="utf-8"))["release_fingerprint"] == published_release["fingerprint"]

    second = module.refresh_phase0_artifacts(
        optimizer_fixture_path=optimizer_fixture_path,
        corpus_release_path=corpus_release_path,
        corpus_active_release_path=corpus_active_release_path,
        corpus_stage_release_path=corpus_stage_release_path,
    )

    assert second["updated_paths"] == []
