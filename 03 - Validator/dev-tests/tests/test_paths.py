from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from validator_vision.paths import (
    app_home,
    bundled_config_path,
    default_config_path,
    default_output_dir,
    ensure_app_layout,
    log_dir,
)
from validator_vision.paths import repository as path_repository
from validator_vision.paths import workflow as path_workflow


def test_default_paths_follow_validator_home_override(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path):
    home = scratch_dir / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))
    assert app_home() == home
    assert default_config_path() == home / "config" / "config.json"
    assert default_output_dir() == home / "output"
    assert log_dir() == home / "logs"


def test_ensure_app_layout_seeds_default_config_into_app_home(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path):
    home = scratch_dir / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))
    returned_home = ensure_app_layout()
    seeded_path = default_config_path()
    assert returned_home == home
    assert seeded_path.exists()
    assert seeded_path.read_text(encoding="utf-8") == bundled_config_path().read_text(encoding="utf-8")


def test_ensure_app_layout_seeds_config_safely_under_concurrency(scratch_dir: Path):
    home = scratch_dir / "validator-home"
    barrier = threading.Barrier(8)
    errors: list[str] = []

    def _ensure() -> None:
        try:
            barrier.wait()
            ensure_app_layout(home)
        except Exception as exc:  # pragma: no cover - failure path asserted below
            errors.append(repr(exc))

    threads = [threading.Thread(target=_ensure) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert default_config_path(home).read_text(encoding="utf-8") == bundled_config_path().read_text(encoding="utf-8")


def test_ensure_app_layout_does_not_fallback_after_selected_home_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    scratch_dir: Path,
):
    home = scratch_dir / "validator-home"
    monkeypatch.setenv("VALIDATOR_VISION_HOME", str(home))
    calls: list[Path] = []

    def _raise(layout):
        calls.append(layout.app_home)
        raise OSError("locked")

    monkeypatch.setattr(path_workflow.repository, "ensure_app_layout", _raise)

    with pytest.raises(OSError, match="locked"):
        path_workflow.ensure_app_layout()

    assert calls == [home]


def test_seed_default_config_keeps_final_path_absent_when_promotion_fails(
    monkeypatch: pytest.MonkeyPatch,
    scratch_dir: Path,
):
    source = scratch_dir / "bundled" / "config.json"
    target = scratch_dir / "home" / "config" / "config.json"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_text('{"ok": true}', encoding="utf-8")

    def _raise_rename(self, target_path):
        del self, target_path
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "rename", _raise_rename)

    with pytest.raises(PermissionError, match="locked"):
        path_repository._seed_default_file(target, source)

    assert not target.exists()
    assert list(target.parent.glob("cfg-*.tmp")) == []


def test_ensure_app_layout_migrates_legacy_row_matching_defaults(scratch_dir: Path):
    home = scratch_dir / "validator-home"
    config_path = default_config_path(home)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "checks": {
                    "free_text": True,
                    "context_scalars": True,
                    "content_fields": True,
                    "rows": True,
                },
                "match": {
                    "scalar_level": "FAIL",
                    "row_level": "WARN",
                    "require_free_text": True,
                    "number_tolerance_absolute": 0.01,
                    "min_string_length": 4,
                    "min_compact_length": 5,
                    "context_fields": ["company"],
                    "skip_content_fields": ["_source_refs"],
                    "skip_row_fields": ["_source_refs"],
                    "row_anchor_keys": ["position", "description", "label", "item", "title", "name"],
                },
                "flag_needs_review": True,
                "max_issues_per_check": 20,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    ensure_app_layout(home)

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["match"]["skip_row_fields"] == ["_source_refs", "page", "sequence", "confidence"]
    assert payload["match"]["row_anchor_keys"] == [
        "position",
        "description",
        "label",
        "item",
        "title",
        "name",
        "question",
        "text",
        "content",
        "value",
        "summary",
    ]
