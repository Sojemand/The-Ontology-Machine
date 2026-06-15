from __future__ import annotations

import copy
import json
from pathlib import Path

from llm_interpreter.interpreter import process_single
from llm_interpreter.models import InterpreterConfig
from tests.support.provider_stubs import MockProvider


def clone_request(sample_request: dict) -> dict:
    return copy.deepcopy(sample_request)


def write_request(path: Path, request: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request), encoding="utf-8")
    return path


def process_request_file(
    request_file: Path,
    output_path: Path,
    *,
    config: InterpreterConfig | None = None,
    response_json: dict | None = None,
) -> dict:
    return process_single(
        request_file,
        output_path,
        config or InterpreterConfig(),
        MockProvider(response_json=response_json or {}),
    )


def process_request_object(
    request: dict,
    output_path: Path,
    *,
    config: InterpreterConfig | None = None,
    response_json: dict | None = None,
) -> dict:
    return process_single(
        request,
        output_path,
        config or InterpreterConfig(),
        MockProvider(response_json=response_json or {}),
    )
