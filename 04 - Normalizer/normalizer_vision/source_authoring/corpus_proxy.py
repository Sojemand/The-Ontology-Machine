"""Owner-local subprocess bridge to the Corpus Builder activation contract."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from ..models.serialization import atomic_json_write

_CONTRACT_MODULE = "corpus_builder.orchestrator_contract"
_CORPUS_BUILDER_DIR = "05 - Corpus Builder"
_DEFAULT_CONTRACT_TIMEOUT_SECONDS = 1800
_ISOLATED_ENV_KEYS = (
    "PYTHONHOME",
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "__PYVENV_LAUNCHER__",
    "TCL_LIBRARY",
    "TK_LIBRARY",
)


def activate_release(project_root: Path, *, release_path: str, corpus_db_path: str) -> dict[str, object]:
    module_root = _corpus_builder_root(project_root)
    payload = {
        "action": "activate_semantic_release",
        "release_path": release_path,
        "corpus_db_path": corpus_db_path,
    }
    return _invoke_contract(module_root, payload)


def create_and_activate_new_corpus_db(project_root: Path, *, release_path: str, confirmation_artifact_path: str) -> dict[str, object]:
    module_root = _corpus_builder_root(project_root)
    payload = {
        "action": "create_and_activate_new_corpus_db",
        "release_path": release_path,
        "confirmation_artifact_path": confirmation_artifact_path,
    }
    return _invoke_contract(module_root, payload)


def _corpus_builder_root(project_root: Path) -> Path:
    explicit = os.getenv("NORMALIZER_CORPUS_BUILDER_HOME", "").strip()
    if explicit:
        root = Path(explicit)
    else:
        pipeline_root = os.getenv("VISION_PIPELINE_ROOT", "").strip()
        root = Path(pipeline_root) / _CORPUS_BUILDER_DIR if pipeline_root else project_root.parent / _CORPUS_BUILDER_DIR
    if not root.exists():
        raise ValueError(f"Corpus-Builder-Modulpfad fehlt: {root}")
    return root


def _invoke_contract(module_root: Path, payload: dict[str, object]) -> dict[str, object]:
    state_root = module_root / "state"
    state_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="normalizer-corpus-proxy-", dir=str(state_root)) as temp_dir:
        request_path = Path(temp_dir) / "request.json"
        response_path = Path(temp_dir) / "response.json"
        atomic_json_write(request_path, payload)
        timeout = _contract_timeout_seconds()
        try:
            completed = subprocess.run(
                [str(_contract_python(module_root)), "-m", _CONTRACT_MODULE, "--request", str(request_path), "--response", str(response_path)],
                cwd=module_root,
                capture_output=True,
                text=True,
                check=False,
                env=_contract_env(),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Corpus-Builder-Contract Timeout nach {timeout:g}s: {module_root}") from exc
        return _handle_contract_result(completed, response_path)


def _handle_contract_result(completed: subprocess.CompletedProcess, response_path: Path) -> dict[str, object]:
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or f"Contract-Exitcode {completed.returncode}"
        raise RuntimeError(detail.strip())
    if not response_path.exists():
        detail = completed.stderr or completed.stdout or "keine response.json geschrieben"
        raise RuntimeError(f"Corpus-Builder-Contract lieferte keine response.json: {detail.strip()}")
    try:
        payload = json.loads(response_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Corpus-Builder-Contract lieferte ungueltige response.json: {exc}") from exc
    return _normalize_contract_response(payload)


def _contract_timeout_seconds() -> float:
    raw_value = os.getenv("NORMALIZER_CORPUS_BUILDER_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return float(_DEFAULT_CONTRACT_TIMEOUT_SECONDS)
    try:
        parsed = float(raw_value)
    except ValueError:
        raise ValueError("NORMALIZER_CORPUS_BUILDER_TIMEOUT_SECONDS muss eine positive Zahl sein.") from None
    if parsed <= 0:
        raise ValueError("NORMALIZER_CORPUS_BUILDER_TIMEOUT_SECONDS muss eine positive Zahl sein.")
    return parsed


def _normalize_contract_response(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("Corpus-Builder-Contract muss ein JSON-Objekt liefern.")
    detail = payload.get("detail")
    if not isinstance(detail, dict):
        return payload
    merged = dict(detail)
    merged.update({key: value for key, value in payload.items() if key != "detail"})
    return merged


def _contract_python(module_root: Path) -> Path:
    explicit = os.getenv("NORMALIZER_CORPUS_BUILDER_PYTHON", "").strip()
    if explicit:
        python_exe = Path(explicit)
        if not python_exe.exists() or not python_exe.is_file():
            raise ValueError(f"NORMALIZER_CORPUS_BUILDER_PYTHON zeigt auf keine Datei: {python_exe}")
        return python_exe
    runtime_root = module_root / "runtime" / "python"
    if not runtime_root.exists():
        raise ValueError(f"Corpus-Builder-Runtime fehlt: {runtime_root}")
    for candidate in ("python.exe", "Scripts/python.exe", "bin/python"):
        python_exe = runtime_root / candidate
        if python_exe.exists() and python_exe.is_file():
            return python_exe
    raise ValueError(f"Corpus-Builder-Python nicht gefunden in Runtime: {runtime_root}")


def _contract_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _ISOLATED_ENV_KEYS:
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env
