from __future__ import annotations

from typing import Any

import pytest

from mcp_server import tool_handlers
from mcp_server.tools import call_tool


def test_read_translation_glossary_lists_locale_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        assert module_key == "normalizer"
        assert payload["action"] == "read_translation_glossary_locale"
        return {
            "status": "ok",
            "allowed_values": ["de", "en"],
            "value": {
                "active_locale": "de",
                "entries": [{"english_term": "invoice", "canonical": "Rechnung", "aliases": ["Rechnungsbeleg"]}],
            },
        }

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool("read_translation_glossary", {"locale": "de"})

    assert calls == [("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"})]
    assert result["entry_count"] == 1
    assert result["entries"] == [
        {"english_term": "invoice", "canonical": "Rechnung", "aliases": ["Rechnungsbeleg"]}
    ]
    assert result["entry_status"] == "unchanged"
    assert result["glossary_exists"] is True


def test_upsert_translation_glossary_entry_validates_and_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        assert module_key == "normalizer"
        if payload["action"] == "read_translation_glossary_locale":
            return {
                "status": "ok",
                "allowed_values": ["de", "en"],
                "value": {
                    "active_locale": "de",
                    "entries": [{"english_term": "invoice", "canonical": "Rechnung", "aliases": ["Rechnungsbeleg"]}],
                },
            }
        return {"status": "ok", "value": payload["value"]}

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool(
        "upsert_translation_glossary_entry",
        {
            "locale": "de",
            "english_term": "receipt",
            "canonical": "Beleg",
            "aliases": ["Zahlungsbeleg", "Zahlungsbeleg"],
        },
    )

    expected_entries = [
        {"english_term": "invoice", "canonical": "Rechnung", "aliases": ["Rechnungsbeleg"]},
        {"english_term": "receipt", "canonical": "Beleg", "aliases": ["Zahlungsbeleg"]},
    ]
    assert calls == [
        ("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"}),
        (
            "normalizer",
            {
                "action": "validate_surface",
                "surface_id": "normalizer.translation_glossary",
                "value": {"active_locale": "de", "entries": expected_entries},
            },
        ),
        (
            "normalizer",
            {
                "action": "write_surface",
                "surface_id": "normalizer.translation_glossary",
                "value": {"active_locale": "de", "entries": expected_entries},
            },
        ),
    ]
    assert result["entry_status"] == "created"
    assert result["entries"] == expected_entries


def test_remove_translation_glossary_entry_reports_not_found_without_write(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_invoke(module_key: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        calls.append((module_key, payload))
        assert module_key == "normalizer"
        return {
            "status": "ok",
            "allowed_values": ["de", "en"],
            "value": {
                "active_locale": "de",
                "entries": [{"english_term": "invoice", "canonical": "Rechnung", "aliases": []}],
            },
        }

    monkeypatch.setattr(tool_handlers, "_invoke_edit", fake_invoke)

    result = call_tool(
        "remove_translation_glossary_entry",
        {"locale": "de", "english_term": "receipt"},
    )

    assert calls == [("normalizer", {"action": "read_translation_glossary_locale", "locale": "de"})]
    assert result["entry_status"] == "not_found"
    assert result["english_term"] == "receipt"
