"""Named contract types shared between subprocess stages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

INTERPRET_DOCUMENT_ACTION = "interpret_document"
HEALTHCHECK_ACTION = "healthcheck"
DEBUG_RUN_ACTION = "debug_run"
GENERATE_LLM_ACTION = "generate_llm"
ActionName = Literal["interpret_document", "healthcheck", "debug_run", "generate_llm"]
DebugRunMode = Literal["single", "batch"]


@dataclass(frozen=True)
class InterpreterRuntimeSettings:
    model: str
    max_output_tokens: int


@dataclass(frozen=True)
class InterpretDocumentCommand:
    request_path: Path
    structured_output_path: Path
    runtime_settings: InterpreterRuntimeSettings
    debug_bundle_dir: Path | None = None


@dataclass(frozen=True)
class HealthcheckCommand:
    runtime_settings: InterpreterRuntimeSettings


@dataclass(frozen=True)
class DebugRunCommand:
    session_root: Path
    mode: DebugRunMode
    request_path: Path | None
    input_root: Path | None
    output_root: Path
    num_workers: int
    runtime_settings: InterpreterRuntimeSettings


@dataclass(frozen=True)
class GenerateLLMCommand:
    runtime_settings: InterpreterRuntimeSettings
    messages: tuple[dict, ...]
    target_schema: dict | None
    max_output_tokens: int
