from __future__ import annotations

import json
from pathlib import Path

from tests.tool_contract_matrix_types import GoldenCase

GLOSSARY_ENTRIES = [
    {"english_term": "invoice", "canonical": "Rechnung", "aliases": ["Rechnungsbeleg"]},
    {"english_term": "receipt", "canonical": "Beleg", "aliases": ["Zahlungsbeleg"]},
]


def cases() -> list[GoldenCase]:
    return [
        GoldenCase(
            "orchestrator.healthcheck",
            lambda _p: {},
            product_calls=lambda _p: [("orchestrator", {"action": "healthcheck"})],
        ),
        GoldenCase(
            "orchestrator.reset",
            lambda _p: {},
            product_calls=lambda p: [
                ("orchestrator", {"action": "reset", "ui_state": _active_orchestrator_ui_state(p)})
            ],
        ),
        GoldenCase(
            "read_translation_glossary",
            lambda _p: {"locale": "de"},
            edit_calls=lambda _p: [("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"})],
        ),
        GoldenCase(
            "upsert_translation_glossary_entry",
            lambda _p: {
                "locale": "de",
                "english_term": "receipt",
                "canonical": "Beleg",
                "aliases": ["Zahlungsbeleg", "Zahlungsbeleg"],
            },
            edit_calls=lambda _p: [
                ("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"}),
                _surface_call("validate_surface", GLOSSARY_ENTRIES),
                _surface_call("write_surface", GLOSSARY_ENTRIES),
            ],
        ),
        GoldenCase(
            "remove_translation_glossary_entry",
            lambda _p: {"locale": "de", "english_term": "invoice"},
            edit_calls=lambda _p: [
                ("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"}),
                _surface_call("validate_surface", []),
                _surface_call("write_surface", []),
            ],
        ),
    ]


def _surface_call(action: str, entries: list[dict]) -> tuple[str, dict]:
    return (
        "normalizer",
        {
            "action": action,
            "surface_id": "normalizer.translation_glossary",
            "value": {"active_locale": "de", "entries": entries},
        },
    )


def _active_orchestrator_ui_state(paths: dict[str, str]) -> dict:
    return json.loads(Path(paths["orchestrator_ui_state_path"]).read_text(encoding="utf-8"))
