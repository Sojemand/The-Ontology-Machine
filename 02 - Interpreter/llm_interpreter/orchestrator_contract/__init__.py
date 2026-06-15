"""Path-stable surface for the merged Interpreter subprocess contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..interpreter import process_batch, process_single
from ..interpreter.adapter import load_request_payload
from ..models import load_config
from ..providers import create_provider
from ..runtime_support import load_dotenv, setup_logging
from . import adapter, generate_action, validation, workflow
from .types import (
    DEBUG_RUN_ACTION,
    GENERATE_LLM_ACTION,
    HEALTHCHECK_ACTION,
    INTERPRET_DOCUMENT_ACTION,
    ActionName,
    DebugRunCommand,
    GenerateLLMCommand,
    HealthcheckCommand,
    InterpreterRuntimeSettings,
    InterpretDocumentCommand,
)


def _load_request(path: Path) -> dict:
    return adapter.load_request(path)


def _write_response(path: Path, payload: dict) -> None:
    adapter.write_response(path, payload)


def _interpret_document(payload: dict) -> dict:
    return workflow.interpret_document(
        payload,
        load_dotenv_fn=load_dotenv,
        load_config_fn=load_config,
        parse_interpret_document_command_fn=validation.parse_interpret_document_command,
        load_request_payload_fn=load_request_payload,
        process_single_fn=process_single,
    )


def _healthcheck(payload: dict) -> dict:
    return workflow.healthcheck(
        payload,
        load_dotenv_fn=load_dotenv,
        load_config_fn=load_config,
        parse_healthcheck_command_fn=validation.parse_healthcheck_command,
        create_provider_fn=create_provider,
    )


def _debug_run(payload: dict) -> dict:
    return workflow.debug_run(
        payload,
        load_dotenv_fn=load_dotenv,
        load_config_fn=load_config,
        parse_debug_run_command_fn=validation.parse_debug_run_command,
        load_request_payload_fn=load_request_payload,
        process_single_fn=process_single,
        process_batch_fn=process_batch,
    )


def _generate_llm(payload: dict) -> dict:
    return generate_action.generate_llm(
        payload,
        load_dotenv_fn=load_dotenv,
        load_config_fn=load_config,
        parse_generate_llm_command_fn=validation.parse_generate_llm_command,
        create_provider_fn=create_provider,
    )


def _dispatch(payload: dict) -> dict:
    return workflow.dispatch(
        payload,
        require_action_fn=validation.require_action,
        interpret_document_fn=_interpret_document,
        healthcheck_fn=_healthcheck,
        debug_run_fn=_debug_run,
        generate_llm_fn=_generate_llm,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args(argv)
    setup_logging()
    try:
        response = _dispatch(_load_request(Path(args.request)))
    except Exception as exc:  # pragma: no cover
        response = workflow.error_response(str(exc))
    _write_response(Path(args.response), response)
    return 0


__all__ = [
    "ActionName",
    "DEBUG_RUN_ACTION",
    "GENERATE_LLM_ACTION",
    "GenerateLLMCommand",
    "HealthcheckCommand",
    "HEALTHCHECK_ACTION",
    "INTERPRET_DOCUMENT_ACTION",
    "InterpreterRuntimeSettings",
    "InterpretDocumentCommand",
    "DebugRunCommand",
    "_dispatch",
    "_debug_run",
    "_generate_llm",
    "_healthcheck",
    "_interpret_document",
    "_load_request",
    "_write_response",
    "adapter",
    "create_provider",
    "load_dotenv",
    "load_config",
    "main",
    "process_single",
    "process_batch",
    "setup_logging",
    "validation",
    "workflow",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
