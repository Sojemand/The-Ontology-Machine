"""Tests for config loading and repo defaults."""
from __future__ import annotations

from pathlib import Path

import pytest

import ingestion_layer_file.paths.workflow as file_paths_workflow
from ingestion_layer_vision.models import load_config


def test_config_loads_shared_fixture(config_yaml_path):
    config = load_config(config_yaml_path)

    assert config.max_file_size_mb == 100
    assert config.max_blocks_per_file == 50000
    assert config.max_cell_text_length == 8000
    assert config.processing_order == "input"
    assert config.plugin_timeout_seconds == 120
    assert config.parallel_workers == 1


def test_repo_config_matches_expected_defaults():
    project_root = Path(__file__).resolve().parents[2]
    config = load_config(project_root / "config" / "config.yaml")

    assert config.max_file_size_mb == 100
    assert config.max_blocks_per_file == 50000
    assert config.max_cell_text_length == 8000
    assert config.processing_order == "input"
    assert config.plugin_timeout_seconds == 120
    assert config.parallel_workers == 4


def test_vision_config_accepts_shared_file_render_fields(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "max_file_size_mb: 100",
                "max_blocks_per_file: 50000",
                "max_cell_text_length: 8000",
                "processing_order: input",
                "plugin_timeout_seconds: 120",
                "parallel_workers: 4",
                "render_dpi: 150",
                "render_width_px: 1240",
                "render_height_px: 1754",
                "page_margin_pt: 54",
                "default_font_size_pt: 10",
                "code_font_size_pt: 9",
                "heading_font_size_pt: 16",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.parallel_workers == 4
    assert not hasattr(config, "render_width_px")


def test_file_config_migration_uses_atomic_publication(monkeypatch, tmp_path: Path) -> None:
    bundled_config = tmp_path / "bundled" / "config.yaml"
    app_config = tmp_path / "app" / "config.yaml"
    bundled_config.parent.mkdir()
    app_config.parent.mkdir()
    bundled_config.write_text("max_cell_text_length: 8000\n", encoding="utf-8")
    app_config.write_text("max_cell_text_length: 2000\n", encoding="utf-8")
    calls: list[tuple[Path, str]] = []

    def fake_atomic_text_write(path: Path, text: str) -> None:
        calls.append((path, text))
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(file_paths_workflow, "atomic_text_write", fake_atomic_text_write)

    file_paths_workflow._seed_or_migrate_config(app_config, bundled_config)

    assert calls and calls[0][0] == app_config
    assert "max_cell_text_length: 8000" in app_config.read_text(encoding="utf-8")


def test_file_config_migration_failed_publication_preserves_existing_config(monkeypatch, tmp_path: Path) -> None:
    bundled_config = tmp_path / "bundled" / "config.yaml"
    app_config = tmp_path / "app" / "config.yaml"
    bundled_config.parent.mkdir()
    app_config.parent.mkdir()
    bundled_config.write_text("max_cell_text_length: 8000\n", encoding="utf-8")
    app_config.write_text("max_cell_text_length: 2000\n", encoding="utf-8")
    monkeypatch.setattr(
        file_paths_workflow,
        "atomic_text_write",
        lambda _path, _text: (_ for _ in ()).throw(PermissionError("locked")),
    )

    with pytest.raises(PermissionError, match="locked"):
        file_paths_workflow._seed_or_migrate_config(app_config, bundled_config)

    assert app_config.read_text(encoding="utf-8") == "max_cell_text_length: 2000\n"

