from __future__ import annotations

import json

import os

import subprocess

import sys

from pathlib import Path

from types import SimpleNamespace

import pytest

import yaml

from normalizer_vision.source_authoring import corpus_proxy

from normalizer_vision.source_authoring import operations as source_operations

from normalizer_vision.taxonomy_compile import ensure_compiled_taxonomy_assets

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGRESSION_ROOT = PROJECT_ROOT / "dev-tests" / "fixtures" / "regression"

def _run_contract(tmp_root: Path, payload: dict) -> dict:
    request_path = tmp_root / "state" / "edit-contract.request.json"
    response_path = tmp_root / "state" / "edit-contract.response.json"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["NORMALIZER_VISION_HOME"] = str(tmp_root)
    completed = subprocess.run(
        [sys.executable, "-m", "normalizer_vision.edit_contract", "--request", str(request_path), "--response", str(response_path)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))

def _term(payload: dict, section_id: str, term_id: str) -> dict:
    return next(item for item in payload[section_id] if item["term_id"] == term_id)

def _compiled_assets(project_root: Path):
    compiled = ensure_compiled_taxonomy_assets(project_root)
    assert compiled is not None
    return compiled

def _assert_hint_envelope(payload: dict) -> None:
    assert payload["status"] == "ok"
    assert isinstance(payload.get("allowed_values"), list)
    assert isinstance(payload.get("required_fields"), list)
    assert isinstance(payload.get("references_existing_codes"), list)
    assert isinstance(payload.get("used_by_modules"), list)
    assert isinstance(payload.get("validation_risks"), list)
    assert isinstance(payload.get("compile_effect"), str)
    assert isinstance(payload.get("prompt_effect"), str)
    assert isinstance(payload.get("corpus_effect"), str)

__all__ = [name for name in globals() if not name.startswith("__")]
