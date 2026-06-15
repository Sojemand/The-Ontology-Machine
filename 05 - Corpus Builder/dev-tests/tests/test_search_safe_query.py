"""Safe query tests for Corpus Builder Vision."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_builder.loader import load_from_file as _load_from_file
from corpus_builder.search import safe_query


def _report_path(json_path: Path) -> Path:
    for suffix in (".vision_validation_report.json", ".validation_report.json"):
        candidate = json_path.with_name(json_path.name.replace(".structured.json", suffix))
        if candidate.exists():
            return candidate
    return json_path.with_name(json_path.name.replace(".structured.json", ".vision_validation_report.json"))


def load_from_file(db, json_path: Path):
    normalized_path = json_path.with_name(json_path.name.replace(".structured.json", ".structured.normalized.json"))
    return _load_from_file(
        db,
        normalized_path,
        _report_path(json_path),
        structured_path=json_path,
    )


def test_safe_query_supports_with_params_and_row_cap(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    for index in range(3):
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["file_path"] = f"C:/docs/query-{index}.pdf"
        structured["source"]["content_hash"] = f"sha256:query-{index}"
        assert load_from_file(
            db,
            make_input_pair(f"query_doc_{index}", structured, vision_report=vision_validation_report),
        ).status == "loaded"

    rows = safe_query(
        db,
        "WITH docs AS (SELECT id, category FROM documents WHERE category = ?) SELECT id FROM docs ORDER BY id",
        params=("finance",),
        max_rows=2,
    )

    assert len(rows) == 2
    assert rows[0]["id"] == "query_doc_0"


def test_safe_query_ignores_literals_and_comments_when_validating_sql(db):
    rows = safe_query(
        db,
        "/* DROP TABLE documents; */ SELECT ';' AS literal, 'DROP' AS keyword; -- trailing comment",
    )

    assert rows == [{"literal": ";", "keyword": "DROP"}]


def test_safe_query_allows_comment_prefixed_cte_without_false_multi_statement(db):
    rows = safe_query(
        db,
        "-- harmless comment with ; and DROP\nWITH sample AS (SELECT 1 AS id) SELECT id FROM sample",
    )

    assert rows == [{"id": 1}]


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("DROP TABLE documents", "Nur SELECT-Statements erlaubt"),
        ("SELECT id FROM documents; SELECT id FROM documents", "Nur genau ein SQL-Statement erlaubt"),
        ("SELECT id FROM documents WHERE id = 1; PRAGMA table_info(documents)", "Nur genau ein SQL-Statement erlaubt"),
        ("SELECT * FROM documents; DELETE FROM documents", "Nur genau ein SQL-Statement erlaubt"),
        ("PRAGMA table_info(documents)", "Nur SELECT-Statements erlaubt"),
    ],
)
def test_safe_query_rejects_non_readonly_or_multi_statement_sql(db, sql, message):
    with pytest.raises(ValueError, match=message):
        safe_query(db, sql)


def test_safe_query_clamps_non_positive_max_rows(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    for index in range(3):
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["file_path"] = f"C:/docs/maxrows-{index}.pdf"
        structured["source"]["content_hash"] = f"sha256:maxrows-{index}"
        assert load_from_file(
            db,
            make_input_pair(f"maxrows_doc_{index}", structured, vision_report=vision_validation_report),
        ).status == "loaded"

    rows = safe_query(db, "SELECT id FROM documents ORDER BY id", max_rows=0)

    assert len(rows) == 1


def test_safe_query_caps_results_even_when_sql_has_large_limit(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    for index in range(4):
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["file_path"] = f"C:/docs/large-limit-{index}.pdf"
        structured["source"]["content_hash"] = f"sha256:large-limit-{index}"
        assert load_from_file(
            db,
            make_input_pair(
                f"large_limit_doc_{index}",
                structured,
                vision_report=vision_validation_report,
            ),
        ).status == "loaded"

    rows = safe_query(
        db,
        "SELECT id FROM documents ORDER BY id LIMIT 1000",
        max_rows=2,
    )

    assert len(rows) == 2
