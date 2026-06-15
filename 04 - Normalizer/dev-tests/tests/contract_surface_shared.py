from __future__ import annotations

import json

import subprocess

import sys

from pathlib import Path

import pytest

from normalizer_vision.orchestrator_contract import main as contract_main, validation, workflow

from normalizer_vision.semantic_release import build_semantic_release

PROJECT_ROOT = Path(__file__).resolve().parents[2]

__all__ = [name for name in globals() if not name.startswith("__")]
