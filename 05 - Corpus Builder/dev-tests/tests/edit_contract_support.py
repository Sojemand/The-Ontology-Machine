from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COPYTREE_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def _copy_module(tmp_path: Path) -> Path:
    module_root = tmp_path / "corpus_builder_module"
    shutil.copytree(PROJECT_ROOT / "corpus_builder", module_root / "corpus_builder", ignore=COPYTREE_IGNORE)
    shutil.copytree(PROJECT_ROOT / "config", module_root / "config", ignore=COPYTREE_IGNORE)
    shutil.copytree(PROJECT_ROOT / "vision_pipeline_shared", module_root / "vision_pipeline_shared", ignore=COPYTREE_IGNORE)
    shutil.copy2(PROJECT_ROOT / "module-manifest.json", module_root / "module-manifest.json")
    return module_root


def _invoke_contract(module_root: Path, tmp_path: Path, payload: dict) -> dict:
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "corpus_builder.edit_contract",
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=module_root,
        check=False,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))
