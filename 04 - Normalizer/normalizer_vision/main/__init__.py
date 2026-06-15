"""Path-stable headless CLI surface for Normalizer Vision."""
from __future__ import annotations

from ..paths import log_dir, module_root
from . import adapter, types, workflow
from .surface import build_parser, dispatch_command

ROOT = module_root()


def _setup_logging() -> None:
    adapter.setup_logging(resolve_log_dir=lambda: log_dir(ROOT))


def _load_normalizer(config_path: str | None):
    return adapter.load_normalizer(config_path, root=ROOT)


def _run_check_config(args) -> int:
    return workflow.run_check_config(
        types.CheckConfigCommand.from_namespace(args),
        load_normalizer=_load_normalizer,
    )


def _run_analyze_taxonomy(args) -> int:
    return workflow.run_analyze_taxonomy(
        types.AnalyzeTaxonomyCommand.from_namespace(args),
        root=ROOT,
    )


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)
    return dispatch_command(
        args,
        run_check_config=_run_check_config,
        run_analyze_taxonomy=_run_analyze_taxonomy,
    )


__all__ = [
    "ROOT",
    "_load_normalizer",
    "_run_analyze_taxonomy",
    "_run_check_config",
    "_setup_logging",
    "build_parser",
    "main",
]
