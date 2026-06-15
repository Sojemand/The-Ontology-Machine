"""CLI load regression cases for Corpus Builder Vision."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import corpus_builder.main as main_module
from corpus_builder.database import connect
from corpus_builder.main import _run_load
from .fixtures.semantic_context import make_semantic_context


def test_run_load_rejects_structured_input_after_hard_cut(
    tmp_path,
    vision_structured,
    make_input_pair,
):
    json_path = make_input_pair("invoice", vision_structured)
    args = SimpleNamespace(
        input=str(json_path),
        structured_evidence=None,
        validation_report=None,
        corpus_db=str(tmp_path / "corpus.db"),
    )

    with pytest.raises(SystemExit, match="Eingabe muss \\*\\.structured\\.normalized\\.json sein"):
        _run_load(args)


def test_run_load_requires_complete_evidence_pair(
    tmp_path,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
):
    json_path = make_input_pair(
        "invoice",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    normalized_path = json_path.with_name("invoice.structured.normalized.json")
    args = SimpleNamespace(
        input=str(normalized_path),
        structured_evidence=str(json_path),
        validation_report=None,
        corpus_db=str(tmp_path / "corpus.db"),
    )

    with pytest.raises(SystemExit, match="--validation-report ist fuer --structured-evidence Pflicht"):
        _run_load(args)


def test_run_load_single_normalized_file_works(
    tmp_path,
    vision_structured,
    vision_normalized,
    vision_validation_report,
    make_input_pair,
    capsys,
    monkeypatch,
):
    monkeypatch.setattr(main_module, "CONTEXT", make_semantic_context(tmp_path))
    db_path = tmp_path / "corpus.db"
    json_path = make_input_pair(
        "invoice",
        vision_structured,
        vision_report=vision_validation_report,
        normalized=vision_normalized,
    )
    normalized_path = json_path.with_name("invoice.structured.normalized.json")

    args = SimpleNamespace(
        input=str(normalized_path),
        structured_evidence=None,
        validation_report=None,
        corpus_db=str(db_path),
    )

    _run_load(args)

    out = capsys.readouterr().out
    assert "invoice.structured.normalized.json: loaded" in out
    conn = connect(str(db_path))
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    conn.close()
