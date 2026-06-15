from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from corpus_builder.main import corpus_workflow as cli_workflow
from corpus_builder.models import EmbeddingRuntimeSettings
from corpus_builder.search.policy_store import default_search_policy_payload, fulltext_limit_default
from corpus_builder.search.workflow import safe_query
from corpus_builder.services import corpus_workflow as service_workflow


class _FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_cli_search_default_limit_comes_from_search_policy() -> None:
    captured: dict[str, object] = {}
    policy = default_search_policy_payload()
    policy["fulltext"]["limit_default"] = 37

    cli_workflow.run_search(
        SimpleNamespace(query="invoice", limit=None, corpus_db=None),
        context=SimpleNamespace(module_root=Path("C:/module-root")),
        seams=SimpleNamespace(
            load_search_policy=lambda module_root: policy,
            resolve_corpus_db_path=lambda context, corpus_db_path: "C:/db/corpus.db",
            search_corpus=lambda context, **kwargs: captured.update(kwargs) or [],
        ),
    )

    assert captured["limit"] == 37
    assert captured["mode"] == "Volltext (FTS)"

def test_search_corpus_passes_dynamic_promotion_filter_to_fulltext(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    policy = default_search_policy_payload()
    conn = _FakeConnection()

    monkeypatch.setattr(service_workflow, "load_search_policy", lambda module_root: policy)
    monkeypatch.setattr(service_workflow, "resolve_corpus_db_path", lambda context, corpus_db_path: str(tmp_path / "corpus.db"))
    monkeypatch.setattr(service_workflow, "_open_readonly_connection", lambda *args, **kwargs: conn)
    monkeypatch.setattr(service_workflow, "fulltext_search", lambda db, query, **kwargs: captured.update(kwargs) or [])

    service_workflow.search_corpus(
        SimpleNamespace(module_root=tmp_path),
        corpus_db_path=None,
        query="hotel",
        mode="Volltext (FTS)",
        limit=None,
        filters={"promotion:billing_reference": "%ENV%"},
    )

    assert captured["limit"] == fulltext_limit_default(policy)
    assert captured["filters"] == {"promotion:billing_reference": "%ENV%"}
    assert conn.closed is True


def test_search_corpus_passes_hybrid_policy_values_and_filters(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    policy = default_search_policy_payload()
    policy["hybrid"]["top_k_default"] = 9
    policy["hybrid"]["candidate_multiplier"] = 4
    policy["hybrid"]["fts_weight"] = 0.2
    policy["hybrid"]["vec_weight"] = 0.8
    policy["fts"]["normalize_by_max_score"] = False
    conn = _FakeConnection()

    monkeypatch.setattr(service_workflow, "load_search_policy", lambda module_root: policy)
    monkeypatch.setattr(service_workflow, "resolve_corpus_db_path", lambda context, corpus_db_path: str(tmp_path / "corpus.db"))
    monkeypatch.setattr(service_workflow, "_open_readonly_connection", lambda *args, **kwargs: conn)
    monkeypatch.setattr(
        service_workflow,
        "resolve_runtime_capability",
        lambda: SimpleNamespace(status="available", api_key="secret", reason=""),
    )
    monkeypatch.setattr(service_workflow, "hybrid_search", lambda db, query, **kwargs: captured.update(kwargs) or [])

    service_workflow.search_corpus(
        SimpleNamespace(module_root=tmp_path),
        corpus_db_path=None,
        query="invoice",
        mode="Hybrid",
        limit=None,
        filters={"promotion:billing_reference": "%ENV%"},
        runtime_settings=EmbeddingRuntimeSettings(model="test-model"),
    )

    assert captured["top_k"] == 9
    assert captured["candidate_multiplier"] == 4
    assert captured["fts_weight"] == 0.2
    assert captured["vec_weight"] == 0.8
    assert captured["normalize_fts_scores"] is False
    assert captured["filters"] == {"promotion:billing_reference": "%ENV%"}
    assert conn.closed is True


def test_safe_query_uses_policy_row_cap_when_limit_is_omitted(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    policy = default_search_policy_payload()
    policy["readonly"]["max_rows"] = 2
    (config_dir / "search_policy.json").write_text(json.dumps(policy), encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE sample (id INTEGER)")
    conn.executemany("INSERT INTO sample (id) VALUES (?)", [(1,), (2,), (3,)])

    rows = safe_query(conn, "SELECT id FROM sample ORDER BY id", module_root=tmp_path)

    assert rows == [{"id": 1}, {"id": 2}]
