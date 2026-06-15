from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from packaging_contract_support import MODULE_ROOT


def _run_contract(tmp_path: Path, payload: dict) -> dict:
    return _run_contract_with_python(tmp_path, payload, python_args=())


def _run_contract_with_python(
    tmp_path: Path,
    payload: dict,
    *,
    python_args: tuple[str, ...],
    extra_env: dict[str, str] | None = None,
) -> dict:
    app_home = tmp_path / "app_home"
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["OPTIMIZER_HOME"] = str(app_home)
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(
        [
            sys.executable,
            *python_args,
            "-m",
            "ingestion_layer_vision.edit_contract",
            "--request",
            str(request_path),
            "--response",
            str(response_path),
        ],
        cwd=MODULE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(response_path.read_text(encoding="utf-8"))
