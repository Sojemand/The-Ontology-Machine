from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from normalizer_vision.models import load_config, save_config
import normalizer_vision.models.config_io as config_io


def test_load_and_save_config(tmp_project_root: Path):
    config = load_config(tmp_project_root)
    config.taxonomy_profile_id = "operations.default.v1"
    save_config(tmp_project_root, config)
    reloaded = load_config(tmp_project_root)
    assert reloaded.taxonomy_profile_id == "operations.default.v1"


def test_save_config_uses_atomic_text_write(tmp_project_root: Path, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    def fake_atomic_text_write(path: Path, text: str) -> None:
        captured["path"] = path
        captured["text"] = text

    monkeypatch.setattr(config_io, "atomic_text_write", fake_atomic_text_write)
    save_config(tmp_project_root, load_config(tmp_project_root))

    assert captured["path"] == tmp_project_root / "config" / "config.yaml"
    assert "api_key" not in str(captured["text"])
    assert "max_output_tokens" not in str(captured["text"])


def test_load_and_save_config_preserves_advanced_limits(tmp_project_root: Path):
    config = load_config(tmp_project_root)
    config.max_structured_bytes = 2048
    config.max_batch_files = 12
    config.max_batch_workers = 3
    config.default_workers = 3
    save_config(tmp_project_root, config)

    reloaded = load_config(tmp_project_root)

    assert reloaded.max_structured_bytes == 2048
    assert reloaded.max_batch_files == 12
    assert reloaded.max_batch_workers == 3
    assert reloaded.default_workers == 3


def test_load_and_save_config_preserves_projection_hint_mode(tmp_project_root: Path):
    config = load_config(tmp_project_root)
    config.projection_hint_mode = "strict"

    save_config(tmp_project_root, config)

    reloaded = load_config(tmp_project_root)
    assert reloaded.projection_hint_mode == "strict"


def test_save_config_preserves_projection_routing_section(tmp_project_root: Path):
    config = load_config(tmp_project_root)
    config.default_workers = 2

    save_config(tmp_project_root, config)

    saved = yaml.safe_load((tmp_project_root / "config" / "config.yaml").read_text(encoding="utf-8"))
    assert saved["default_workers"] == 2
    assert saved["projection_routing"]["hint_reject_margin"] == 3


def test_save_config_does_not_persist_auth_fields(tmp_project_root: Path):
    config = load_config(tmp_project_root)

    save_config(tmp_project_root, config)

    saved_text = (tmp_project_root / "config" / "config.yaml").read_text(encoding="utf-8")
    assert "api_key" not in saved_text
    assert "api_base_url" not in saved_text
    assert "model" not in saved_text
    assert "max_output_tokens" not in saved_text
    assert "thinking_effort" not in saved_text
