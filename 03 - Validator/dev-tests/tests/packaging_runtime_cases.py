from __future__ import annotations

import json

from packaging_support import (
    CHECK_RUNTIME,
    MODULE_ROOT,
    RUNTIME_MANIFEST,
    RUNTIME_PYTHON,
    RUNTIME_ROOT,
    _run_batch,
    _run_command,
)


def test_bundled_runtime_provenance_is_self_contained() -> None:
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    completed = _run_command(
        [str(RUNTIME_PYTHON), "-c", "import encodings, json, sys; print(json.dumps({'version': sys.version.split()[0], 'encodings': encodings.__file__}))"],
        cwd=MODULE_ROOT,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    runtime_root = str(RUNTIME_ROOT.resolve()).lower()
    assert payload["version"].startswith(manifest["python_version"])
    assert str(payload["encodings"]).lower().startswith(runtime_root)


def test_runtime_checker_reports_portable_runtime() -> None:
    completed = _run_batch(CHECK_RUNTIME, cwd=MODULE_ROOT)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["python"]["path"].lower().endswith("runtime\\python\\python.exe")
    assert payload["provenance"]["encodings"].lower().startswith(str(RUNTIME_ROOT.resolve()).lower())
