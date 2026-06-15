from __future__ import annotations

from llm_interpreter.orchestrator_contract import _dispatch, _healthcheck, _interpret_document


def test_dispatch_returns_error_for_unknown_action() -> None:
    result = _dispatch({"action": "unknown"})

    assert result["status"] == "error"
    assert "Unbekannte Aktion" in result["error"]


def test_interpret_document_requires_request_and_output_paths() -> None:
    assert _interpret_document({}) == {"status": "error", "error": "request_path fehlt."}
    assert _interpret_document({"request_path": "x"}) == {"status": "error", "error": "structured_output_path fehlt."}


def test_healthcheck_requires_runtime_settings() -> None:
    assert _healthcheck({}) == {"status": "error", "error": "runtime_settings fehlt."}


def test_interpret_document_requires_runtime_settings_after_paths() -> None:
    assert (
        _interpret_document({"request_path": "x", "structured_output_path": "y"})
        == {"status": "error", "error": "runtime_settings fehlt."}
    )
