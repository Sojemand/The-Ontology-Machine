from __future__ import annotations

from orchestrator.ui import debug_help, status_help


def test_corpus_builder_debug_help_documents_release_requirement_and_embedding_boundary() -> None:
    title, body = debug_help.get_help("corpus_builder") or ("", "")

    assert title == "Corpus Builder Debug Guide"
    assert "SEMANTIC RELEASE" in body
    assert "already active release" in body
    assert "pipeline aborts at start" in body
    assert "normal orchestrated pipeline runs embeddings automatically" in body
    assert "this debug run keeps rebuilds isolated" in body


def test_status_help_documents_release_precondition_for_normal_runs() -> None:
    assert "Corpus Builder must already have an active release" in status_help.STATUS_BODY
    assert "pipeline aborts at start" in status_help.STATUS_BODY
    assert "Embeddings run automatically after successful corpus loads" in status_help.STATUS_BODY
    assert "Open Edit Suite" in status_help.STATUS_BODY
    assert "owner-provided edit surfaces" in status_help.STATUS_BODY
