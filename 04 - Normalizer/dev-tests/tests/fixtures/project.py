from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from normalizer_vision.models import NormalizerRuntimeSettings
from normalizer_vision.taxonomy_compile import compile_source_package
from normalizer_vision.taxonomy_sources import load_source_package

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def tmp_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "normalizer_project"
    (root / "config").mkdir(parents=True)
    (root / "output").mkdir(parents=True)
    (root / "state").mkdir(parents=True)
    shutil.copy(PROJECT_ROOT / "module-manifest.json", root / "module-manifest.json")
    shutil.copy(PROJECT_ROOT / "config" / "config.yaml", root / "config" / "config.yaml")
    source_root = PROJECT_ROOT / "config" / "taxonomy_sources"
    if source_root.exists():
        shutil.copytree(source_root, root / "config" / "taxonomy_sources")
    blueprint_root = PROJECT_ROOT / "config" / "taxonomy_blueprints"
    if blueprint_root.exists():
        shutil.copytree(blueprint_root, root / "config" / "taxonomy_blueprints")
    shutil.copy(PROJECT_ROOT / "config" / "prompt_bundle.json", root / "config" / "prompt_bundle.json")
    shutil.copy(PROJECT_ROOT / "config" / "prompt_overrides.json", root / "config" / "prompt_overrides.json")
    shutil.copy(PROJECT_ROOT / "config" / "semantic_release.recipe.json", root / "config" / "semantic_release.recipe.json")
    return root


@pytest.fixture()
def sample_structured_file(tmp_project_root: Path, sample_structured_input: dict) -> Path:
    path = tmp_project_root / "sample.pdf.structured.json"
    path.write_text(json.dumps(sample_structured_input), encoding="utf-8")
    return path


@pytest.fixture()
def sample_batch_dir(tmp_project_root: Path, sample_structured_input: dict) -> Path:
    batch_dir = tmp_project_root / "batch"
    batch_dir.mkdir(parents=True)
    for index in range(2):
        path = batch_dir / f"sample_{index}.pdf.structured.json"
        path.write_text(json.dumps(sample_structured_input), encoding="utf-8")
    return batch_dir


@pytest.fixture()
def operations_profile_path(tmp_project_root: Path) -> str:
    return "operations.default.v1"


@pytest.fixture()
def normalizer_runtime_settings() -> NormalizerRuntimeSettings:
    return NormalizerRuntimeSettings(model="gpt-5.4-mini", max_output_tokens=15_000)


def compiled_taxonomy_assets(project_root: Path):
    compiled = compile_source_package(load_source_package(project_root))
    return compiled
