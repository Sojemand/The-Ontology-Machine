from __future__ import annotations

from pathlib import Path

from corpus_builder.main.surface import build_parser

MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_cli_parser_has_no_local_credentials_commands() -> None:
    parser = build_parser()
    subparsers_action = next(action for action in parser._actions if getattr(action, "choices", None))

    forbidden = {"providers", "login", "logout", "save-key", "delete-key", "check-api"}
    assert forbidden.isdisjoint(subparsers_action.choices)

def test_module_has_no_local_gui_surface_left() -> None:
    assert not list((MODULE_ROOT / "corpus_builder" / "ui").glob("*.py"))


def test_module_has_no_local_keystore_source() -> None:
    keystore_dir = MODULE_ROOT / "corpus_builder" / "keystore"

    assert not list(keystore_dir.glob("*.py"))
