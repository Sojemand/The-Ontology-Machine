from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validator_vision.models import ValidatorConfig, load_config


TEST_DATA = Path(__file__).parent / "test_data"


@pytest.fixture()
def default_config() -> ValidatorConfig:
    return load_config(Path(__file__).parent.parent.parent / "config" / "config.json")


@pytest.fixture()
def scratch_dir() -> Path:
    base_dir = Path(__file__).parent.parent.parent / ".tmp" / "pytest"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def tmp_report_root(scratch_dir: Path) -> Path:
    report_root = scratch_dir / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    return report_root


