from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from edit_suite.registry.types import ModuleReadinessEntry
from edit_suite.surfaces.load_bundle import load_bundle
from edit_suite.surfaces.types import ModuleSurfaceBundle

MODULE_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = MODULE_ROOT.parent


@pytest.fixture()
def scratch_dir() -> Path:
    path = Path(tempfile.mkdtemp(prefix="edit-suite-tests-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def normalizer_entry() -> ModuleReadinessEntry:
    module_root = PIPELINE_ROOT / "04 - Normalizer"
    return ModuleReadinessEntry(
        slot_name=module_root.name,
        display_name="Normalizer",
        module_root=str(module_root.resolve()),
        module_key="normalizer",
        readiness="ready",
        blockers=(),
        manifest_path=str((module_root / "module-manifest.json").resolve()),
        manifest_present=True,
        edit_contract_path=str((module_root / "normalizer_vision" / "edit_contract").resolve()),
        runtime_available=True,
    )


@pytest.fixture(scope="session")
def normalizer_bundle(normalizer_entry: ModuleReadinessEntry, tmp_path_factory: pytest.TempPathFactory) -> ModuleSurfaceBundle:
    module_root = Path(normalizer_entry.module_root)
    state_root = tmp_path_factory.mktemp("normalizer-bundle-state") / "state"
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("NORMALIZER_VISION_HOME", str(module_root.resolve()))
        return load_bundle(normalizer_entry, state_root=state_root)
