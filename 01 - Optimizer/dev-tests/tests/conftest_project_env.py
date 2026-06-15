"""Project-root and config fixtures for Optimizer dev-tests."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ingestion_layer_vision.models import IngestionConfig


def _default_config_payload() -> dict:
    return {
        "max_file_size_mb": 100,
        "max_blocks_per_file": 50000,
        "max_cell_text_length": 8000,
        "processing_order": "input",
        "plugin_timeout_seconds": 120,
        "parallel_workers": 1,
    }


def write_config_yaml(config_dir: Path, payload: dict | None = None) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(payload or _default_config_payload(), sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def build_project_root(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    root = tmp_path / "project"
    input_dir = root / "input"
    output_dir = root / "output"
    state_dir = root / "state"
    config_dir = root / "config"
    plugins_dir = root / "plugins"
    input_dir.mkdir(parents=True)
    output_dir.mkdir()
    state_dir.mkdir()
    config_dir.mkdir()
    plugins_dir.mkdir()
    write_config_yaml(config_dir)
    return root, input_dir, output_dir, state_dir, config_dir, plugins_dir


@pytest.fixture
def project_env(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    state_dir = tmp_path / "state"
    input_dir.mkdir()
    output_dir.mkdir()
    state_dir.mkdir()
    return input_dir, output_dir, state_dir


@pytest.fixture
def default_config():
    return IngestionConfig()


@pytest.fixture
def config_yaml_path(tmp_path):
    return write_config_yaml(tmp_path / "config")


@pytest.fixture
def project_root_env(tmp_path):
    root, input_dir, output_dir, state_dir, config_dir, plugins_dir = build_project_root(tmp_path)
    return root, input_dir, output_dir, state_dir, {"config_dir": config_dir, "plugins_dir": plugins_dir}


@pytest.fixture
def tmp_state_dir(project_env):
    _input_dir, _output_dir, state_dir = project_env
    return state_dir


@pytest.fixture
def tmp_config_dir(tmp_path):
    config_dir = tmp_path / "config"
    write_config_yaml(
        config_dir,
        {
            "max_file_size_mb": 100,
            "max_blocks_per_file": 5000,
            "max_cell_text_length": 8000,
            "processing_order": "input",
            "plugin_timeout_seconds": 120,
        },
    )
    return config_dir


@pytest.fixture
def tmp_plugins_dir(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


@pytest.fixture
def tmp_output_dir(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "raw_extracts").mkdir()
    return output_dir


@pytest.fixture
def scratch_dir(tmp_path) -> Path:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return scratch


@pytest.fixture
def sample_input_dir(tmp_path) -> Path:
    input_dir = tmp_path / "input"
    nested_dir = input_dir / "customer" / "2024"
    nested_dir.mkdir(parents=True)
    for i in range(5):
        (nested_dir / f"file{i}.xlsx").write_bytes(b"x" * (1000 * (i + 1)))
    for i in range(2):
        (nested_dir / f"doc{i}.pdf").write_bytes(b"p" * (50000 * (i + 1)))
    return input_dir

