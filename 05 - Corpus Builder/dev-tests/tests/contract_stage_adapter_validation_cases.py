from __future__ import annotations

from pathlib import Path

import pytest

from corpus_builder.orchestrator_contract import adapter, validation


def test_adapter_load_request_rejects_non_object_root(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON-Objekt"):
        adapter.load_request(request_path)


def test_adapter_write_response_uses_atomic_json_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_atomic_json_write(path: Path, payload: dict) -> None:
        captured["path"] = path
        captured["payload"] = payload

    monkeypatch.setattr("corpus_builder.orchestrator_contract.adapter.atomic_json_write", fake_atomic_json_write)

    response_path = tmp_path / "response.json"
    payload = {"status": "ok", "reason": "done"}
    adapter.write_response(response_path, payload)

    assert captured == {"path": response_path, "payload": payload}


def test_validation_requires_runtime_settings_for_generate_embeddings() -> None:
    with pytest.raises(ValueError, match="runtime_settings.model fehlt oder ist ungueltig"):
        validation.parse_generate_embeddings_command(
            {"action": "generate_embeddings", "corpus_db_path": "C:/tmp/corpus.db"}
        )


def test_validation_rejects_legacy_embedding_api_fields() -> None:
    with pytest.raises(ValueError, match="Unbekannte Felder: api_key"):
        validation.parse_generate_embeddings_command(
            {
                "action": "generate_embeddings",
                "corpus_db_path": "C:/tmp/corpus.db",
                "runtime_settings": {"model": "text-embedding-3-small"},
                "api_key": "secret",
            }
        )


def test_validation_accepts_healthcheck_scope_with_runtime_settings() -> None:
    command = validation.parse_healthcheck_command(
        {
            "action": "healthcheck",
            "scope": "pipeline_run",
            "runtime_settings": {"model": "text-embedding-3-small"},
        }
    )

    assert command.scope == "pipeline_run"
    assert command.runtime_settings.model == "text-embedding-3-small"


def test_validation_requires_four_path_load_document() -> None:
    command = validation.parse_load_document_command(
        {
            "action": "load_document",
            "corpus_db_path": "C:/tmp/corpus.db",
            "normalized_path": "C:/tmp/doc.structured.normalized.json",
            "structured_path": "C:/tmp/doc.structured.json",
            "validation_path": "C:/tmp/doc.validation_report.json",
        }
    )

    assert command.normalized_path == "C:/tmp/doc.structured.normalized.json"
    assert command.structured_path == "C:/tmp/doc.structured.json"
    assert command.validation_path == "C:/tmp/doc.validation_report.json"


def test_validation_rejects_missing_structured_path() -> None:
    with pytest.raises(ValueError, match="structured_path fehlt oder ist ungueltig"):
        validation.parse_load_document_command(
            {
                "action": "load_document",
                "corpus_db_path": "C:/tmp/corpus.db",
                "normalized_path": "C:/tmp/doc.structured.normalized.json",
            }
        )


def test_validation_rejects_removed_legacy_load_fields() -> None:
    with pytest.raises(ValueError, match="Unbekannte Felder: asset_path, source_file_path"):
        validation.parse_load_document_command(
            {
                "action": "load_document",
                "corpus_db_path": "C:/tmp/corpus.db",
                "normalized_path": "C:/tmp/doc.structured.normalized.json",
                "structured_path": "C:/tmp/doc.structured.json",
                "validation_path": "C:/tmp/doc.validation_report.json",
                "source_file_path": "C:/tmp/doc.pdf",
                "asset_path": "artifacts/page_images/doc.pdf",
            }
        )
