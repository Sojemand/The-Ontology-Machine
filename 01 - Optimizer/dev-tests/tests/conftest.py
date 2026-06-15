"""Shared test bootstrap for Optimizer dev-tests."""
from __future__ import annotations

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[1]

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conftest_processing_env import processing_env  # noqa: F401
from conftest_project_env import (  # noqa: F401
    config_yaml_path,
    default_config,
    project_env,
    project_root_env,
    sample_input_dir,
    scratch_dir,
    tmp_config_dir,
    tmp_output_dir,
    tmp_plugins_dir,
    tmp_state_dir,
)

