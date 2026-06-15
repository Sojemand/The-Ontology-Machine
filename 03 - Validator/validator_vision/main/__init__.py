"""Path-stable surface for Validator Vision CLI and GUI entrypoints."""
from __future__ import annotations

from ..paths import ensure_app_layout, log_dir, module_root
from . import adapter, types, workflow
from .surface import build_parser, dispatch_command

ROOT = module_root()


def _setup_logging() -> None:
    adapter.setup_logging(ensure_layout=ensure_app_layout, resolve_log_dir=log_dir)


def _load_validator_config(config_path: str | None):
    return adapter.load_validator_config(config_path)


def _run_validate(args) -> int:
    return workflow.run_validate(
        types.ValidateCommand.from_namespace(args),
        load_validator_config=_load_validator_config,
    )


def _run_batch(args) -> int:
    return workflow.run_batch(
        types.ValidateBatchCommand.from_namespace(args),
        load_validator_config=_load_validator_config,
    )


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)
    return dispatch_command(
        args,
        run_validate=_run_validate,
        run_batch=_run_batch,
    )


__all__ = ["ROOT", "build_parser", "dispatch_command", "main"]
