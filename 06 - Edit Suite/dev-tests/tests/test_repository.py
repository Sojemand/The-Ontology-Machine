from __future__ import annotations

from pathlib import Path

import pytest

from edit_suite import repository, validation
from edit_suite.surfaces.types import ModuleSurfaceBundle, SurfaceModel


def test_ui_state_roundtrip_stays_inside_state_root(scratch_dir: Path) -> None:
    state_root = scratch_dir / "state"
    repository.ensure_state_layout(state_root)
    repository.save_ui_state(
        state_root,
        {"selected_module": "00 - Orchestrator", "selected_section": "Summary", "window_geometry": "1200x820"},
    )
    loaded = repository.load_ui_state(state_root)
    assert loaded["selected_module"] == "00 - Orchestrator"
    assert loaded["selected_section"] == "Summary"


def test_state_path_validation_rejects_non_state_target(scratch_dir: Path) -> None:
    state_root = scratch_dir / "state"
    repository.ensure_state_layout(state_root)
    with pytest.raises(ValueError, match="outside"):
        validation.ensure_state_child(state_root, scratch_dir / "outside.json")


def test_bundle_cache_roundtrip_normalizes_module_key(scratch_dir: Path) -> None:
    state_root = scratch_dir / "state"
    bundle = ModuleSurfaceBundle(
        source="contract",
        surfaces=(SurfaceModel("normalizer.settings", "Settings", "settings", True, "form", {"source_path": "config/config.yaml"}, {"timeout_seconds": 30}, {"timeout_seconds": 30}, ()),),
    )

    repository.save_bundle_cache(state_root, "04 - Normalizer", bundle.to_dict())
    cached = repository.load_bundle_cache(state_root, "04 - Normalizer")

    assert repository.bundle_cache_path(state_root, "04 - Normalizer").name == "04_normalizer.json"
    assert cached is not None
    loaded = ModuleSurfaceBundle.from_dict(cached)
    assert loaded.surfaces[0].surface_id == "normalizer.settings"


def test_bundle_cache_path_caps_long_module_key(scratch_dir: Path) -> None:
    state_root = scratch_dir / "state"
    module_key = "owner_" + ("segment_" * 45)

    path = repository.bundle_cache_path(state_root, module_key)
    repository.save_bundle_cache(state_root, module_key, {"ok": True})

    assert len(path.stem) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert path.name.endswith(".json")
    assert path == repository.bundle_cache_path(state_root, module_key)
    assert repository.load_bundle_cache(state_root, module_key) == {"ok": True}


def test_corrupt_cache_files_are_ignored(scratch_dir: Path) -> None:
    state_root = scratch_dir / "state"
    repository.ensure_state_layout(state_root)
    repository.registry_cache_path(state_root).write_text("{not json", encoding="utf-8")
    repository.bundle_cache_path(state_root, "04 - Normalizer").parent.mkdir(parents=True)
    repository.bundle_cache_path(state_root, "04 - Normalizer").write_text("[]", encoding="utf-8")

    assert repository.load_registry_cache(state_root) is None
    assert repository.load_bundle_cache(state_root, "04 - Normalizer") is None


def test_safe_filename_removes_path_traversal_segments() -> None:
    assert validation.safe_filename("../snapshot-risk.json", fallback="fallback.json") == "snapshot-risk.json"
    assert validation.safe_filename("..\\..\\risk?.json", fallback="fallback.json") == "risk_.json"


def test_safe_filename_caps_long_owner_names_with_stable_suffix() -> None:
    name = validation.safe_filename("snapshot-risk-" * 20 + ".json", fallback="fallback.json")

    assert len(name) <= validation.MAX_SAFE_FILENAME_LENGTH
    assert name.endswith(".json")
    assert name == validation.safe_filename("snapshot-risk-" * 20 + ".json", fallback="fallback.json")
    assert name != "snapshot-risk-" * 20 + ".json"


def test_atomic_json_write_uses_path_budget_safe_temp_prefix(scratch_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_root = scratch_dir / "state"
    target = state_root / "bundles" / ("very_long_module_name_" * 8 + ".json")
    prefixes: list[str] = []
    real_mkstemp = repository.tempfile.mkstemp

    def capture_mkstemp(*args, **kwargs):
        prefixes.append(str(kwargs.get("prefix", args[0] if args else "")))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(repository.tempfile, "mkstemp", capture_mkstemp)

    repository.atomic_json_write(target, {"ok": True})

    assert prefixes == ["."]
    assert repository.load_json(target) == {"ok": True}
