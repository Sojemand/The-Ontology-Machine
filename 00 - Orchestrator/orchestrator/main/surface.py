"""Surface stage for the orchestrator CLI and GUI entrypoint."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="Standalone end-to-end Orchestrator for the Vision Pipeline",
    )
    parser.add_argument("--gui", action="store_true", default=False, help="GUI starten")
    return parser


def dispatch_command(_args: argparse.Namespace, *, start_gui) -> None:
    start_gui()
