"""Thin parser and dispatch surface for Validator Vision commands."""
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validator-vision",
        description="Profilbewusster Validator fuer structured.json aus vision- und file-Interpretern.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p_validate = sub.add_parser("validate", help="Ein einzelnes structured.json validieren")
    p_validate.add_argument("--structured", required=True, help="Pfad zum structured.json")
    p_validate.add_argument("--report", required=True, help="Exakter Zielpfad fuer den validation_report")
    p_validate.add_argument("--config", default=None, help="Pfad zu einer custom config.json")
    p_validate.add_argument("--raw", default=None, help="Optionaler Pfad zum Raw JSON fuer file-Profile")
    p_validate.add_argument("--raw-root", default=None, help="Optionaler Raw-Ordner fuer file-Profile")

    p_batch = sub.add_parser("validate-batch", help="Ordner mit structured.json-Dateien validieren")
    p_batch.add_argument("--structured", required=True, help="Ordner mit structured.json-Dateien")
    p_batch.add_argument("--report-root", required=True, help="Root fuer exakte validation_report-Ziele")
    p_batch.add_argument("--config", default=None, help="Pfad zu einer custom config.json")
    p_batch.add_argument("--raw-root", default=None, help="Optionaler Raw-Ordner fuer file-Profile")
    return parser


def dispatch_command(
    args,
    *,
    run_validate,
    run_batch,
) -> int:
    if args.command == "validate":
        return run_validate(args)
    if args.command == "validate-batch":
        return run_batch(args)
    raise ValueError(f"Unbekannter Validator-Befehl: {args.command}")
