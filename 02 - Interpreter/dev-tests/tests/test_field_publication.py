from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_interpreter.config_bootstrap import ensure_default_app_config
from llm_interpreter.models import atomic_text_write
from llm_interpreter.orchestrator_contract.adapter import write_response
from llm_interpreter.prompts.bundle import PROMPT_BUNDLE_FILES, default_prompt_bundle, load_prompt_bundle
from llm_interpreter.prompts.schema import get_output_schema
from llm_interpreter.runtime_paths import RUNTIME_HOME_ENV, resolve_runtime_paths


def _hardlink(target: Path, link: Path) -> None:
    try:
        os.link(target, link)
    except OSError as exc:
        pytest.skip(f"hardlink probe unavailable: {exc}")


def test_orchestrator_response_publication_replaces_existing_file(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    link_path = tmp_path / "response.link.json"
    response_path.write_text('{"old": true}', encoding="utf-8")
    _hardlink(response_path, link_path)

    write_response(response_path, {"status": "ok", "value": "ä"})

    assert json.loads(response_path.read_text(encoding="utf-8")) == {"status": "ok", "value": "ä"}
    assert json.loads(link_path.read_text(encoding="utf-8")) == {"old": True}
    assert not response_path.samefile(link_path)


def test_config_bootstrap_routes_prompt_defaults_through_atomic_writer(tmp_path: Path, monkeypatch) -> None:
    paths = resolve_runtime_paths({RUNTIME_HOME_ENV: str(tmp_path / "app-home")})
    calls: list[Path] = []

    def _write(path: Path, text: str) -> None:
        calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr("llm_interpreter.config_bootstrap.atomic_text_write", _write)

    ensure_default_app_config(paths)

    assert sorted(path.name for path in calls) == sorted(PROMPT_BUNDLE_FILES.values())
    assert (paths.config_dir / "prompt_bundle" / "output_schema.json").exists()


def test_prompt_schema_self_heal_replaces_existing_file(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    bundle_dir = config_dir / "prompt_bundle"
    bundle_dir.mkdir(parents=True)
    payload = default_prompt_bundle()
    drifted_schema = get_output_schema()
    drifted_schema["properties"]["processing"]["properties"]["interpreter_profile"] = {
        "type": "string",
        "enum": ["file"],
    }
    for key, filename in PROMPT_BUNDLE_FILES.items():
        value = json.dumps(drifted_schema, indent=2, ensure_ascii=False) if key == "output_schema_json" else payload[key]
        (bundle_dir / filename).write_text(value, encoding="utf-8")
    schema_path = bundle_dir / "output_schema.json"
    link_path = bundle_dir / "output_schema.link.json"
    _hardlink(schema_path, link_path)
    monkeypatch.setenv("INTERPRETER_HOME", str(tmp_path))

    loaded = load_prompt_bundle()

    assert loaded["output_schema_json"] == json.dumps(get_output_schema(), indent=2, ensure_ascii=False)
    assert json.loads(schema_path.read_text(encoding="utf-8")) == get_output_schema()
    assert json.loads(link_path.read_text(encoding="utf-8")) != get_output_schema()
    assert not schema_path.samefile(link_path)


def test_atomic_text_write_uses_short_temp_name_and_retries_locked_replace(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / ("x" * 120 + ".md")
    captured: dict[str, str] = {}
    attempts = {"count": 0}
    original_mkstemp = tempfile.mkstemp
    original_replace = os.replace

    def _mkstemp(*args, **kwargs):
        captured["prefix"] = kwargs["prefix"]
        captured["suffix"] = kwargs["suffix"]
        return original_mkstemp(*args, **kwargs)

    def _replace(src, dst):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError("locked")
        return original_replace(src, dst)

    monkeypatch.setattr("llm_interpreter.models.serialization.tempfile.mkstemp", _mkstemp)
    monkeypatch.setattr("llm_interpreter.models.serialization.os.replace", _replace)
    monkeypatch.setattr("llm_interpreter.models.serialization.time.sleep", lambda _seconds: None)

    atomic_text_write(target, "ok\n")

    assert target.read_text(encoding="utf-8") == "ok\n"
    assert captured == {"prefix": ".", "suffix": ".tmp"}
    assert attempts["count"] == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_text_write_removes_temp_file_after_replace_failures(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "shared.txt"

    monkeypatch.setattr("llm_interpreter.models.serialization.time.sleep", lambda _seconds: None)
    with patch("llm_interpreter.models.serialization.os.replace", side_effect=PermissionError("locked")):
        with pytest.raises(PermissionError, match="locked"):
            atomic_text_write(target, "ok")

    assert not list(tmp_path.glob("*.tmp"))
