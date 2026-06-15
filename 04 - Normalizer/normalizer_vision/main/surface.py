"""Surface stage for the headless maintenance CLI."""
from __future__ import annotations

import argparse
from collections.abc import Callable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normalizer-vision",
        description="Normalizer fuer *.structured.json mit expliziten normalized output targets",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True
    _add_check_config_parser(sub)
    sub.add_parser("analyze-taxonomy", help="Aktuelle Master-Taxonomie und Projections analysieren")
    return parser


def dispatch_command(
    args: argparse.Namespace,
    *,
    run_check_config: Callable[[argparse.Namespace], int],
    run_analyze_taxonomy: Callable[[argparse.Namespace], int],
) -> int:
    if args.command == "check-config":
        return run_check_config(args)
    if args.command == "analyze-taxonomy":
        return run_analyze_taxonomy(args)
    raise ValueError(f"Unbekannter Normalizer-Befehl: {args.command}")


def _add_check_config_parser(subparsers) -> None:
    parser = subparsers.add_parser("check-config", help="Config und Taxonomie pruefen")
    parser.add_argument("--config", default=None, help="Pfad zu einer custom config.yaml")
