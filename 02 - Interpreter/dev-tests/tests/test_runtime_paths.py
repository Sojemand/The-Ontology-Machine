from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from llm_interpreter.runtime_support import load_dotenv, setup_logging
from llm_interpreter.runtime_paths import RUNTIME_HOME_ENV, ensure_state_dir, resolve_runtime_paths


def _module_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_resolve_runtime_paths_prefers_override(tmp_path) -> None:
    paths = resolve_runtime_paths({RUNTIME_HOME_ENV: str(tmp_path / "runtime-home")})

    assert paths.home == (tmp_path / "runtime-home").resolve(strict=False)
    assert paths.env_file == paths.home / "config" / ".env"
    assert paths.state_dir == paths.home / "state"
    assert paths.log_file == paths.home / "logs" / "llm_interpreter.log"
    assert paths.output_dir == paths.home / "output"


def test_resolve_runtime_paths_uses_local_app_data_when_no_override(tmp_path) -> None:
    paths = resolve_runtime_paths({"LOCALAPPDATA": str(tmp_path / "LocalAppData")})

    assert paths.home == (tmp_path / "LocalAppData" / "Enterprise Stack" / "Interpreter").resolve(strict=False)


def test_resolve_runtime_paths_falls_back_to_module_appdata_without_env() -> None:
    paths = resolve_runtime_paths({})

    assert paths.home == (_module_root() / ".appdata").resolve(strict=False)


def test_ensure_state_dir_creates_mutable_state_directory(tmp_path) -> None:
    paths = resolve_runtime_paths({RUNTIME_HOME_ENV: str(tmp_path / "runtime-home")})

    created = ensure_state_dir(paths)

    assert created == paths.state_dir
    assert created.exists()


def test_load_dotenv_reads_per_user_env_file(monkeypatch, tmp_path) -> None:
    runtime_home = tmp_path / "runtime-home"
    env_path = runtime_home / "config" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("OPENAI_API_KEY=sk-test\nLLM_MODEL=gpt-5.4\nLOG_LEVEL=DEBUG\n", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setenv(RUNTIME_HOME_ENV, str(runtime_home))

    load_dotenv()

    assert "OPENAI_API_KEY" not in os.environ
    assert "LLM_MODEL" not in os.environ
    assert os.environ["LOG_LEVEL"] == "DEBUG"


def test_setup_logging_uses_per_user_log_path(monkeypatch, tmp_path) -> None:
    runtime_home = tmp_path / "runtime-home"
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    for handler in list(root.handlers):
        root.removeHandler(handler)
    try:
        monkeypatch.setenv(RUNTIME_HOME_ENV, str(runtime_home))
        setup_logging()
        file_handlers = [handler for handler in root.handlers if isinstance(handler, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename).resolve(strict=False) == (
            runtime_home / "logs" / "llm_interpreter.log"
        ).resolve(strict=False)
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
