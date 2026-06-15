from __future__ import annotations

from validator_vision.validator.raw_claims import collect_raw_claims
from validator_vision.validator.raw_payload import compact_pages_from_payload

from file_profile_fixtures import file_raw


def test_file_profile_ignores_edge_page_number_ocr_blocks():
    raw_payload = file_raw(
        content_hash="sha256:file-page-footer",
        sections=["Gesamtbetrag 318,79 EUR", {"page": 22, "text": "21"}],
    )
    raw_payload["source"]["page_count"] = 26

    claims = collect_raw_claims(raw_payload)

    assert "num:318.79" in claims
    assert "num:21" not in claims


def test_file_profile_ignores_rendered_source_filename_header_for_numeric_claims():
    file_name = "2026-06-08_article_cd66cb6db647.md"
    raw_payload = file_raw(content_hash="sha256:file-source-header", sections=[])
    raw_payload["source"]["file_name"] = file_name
    raw_payload["source"]["file_path"] = f"C:/archive/{file_name}"
    raw_payload["ocr_reference"]["blocks"] = [
        {
            "id": "header_filename",
            "type": "paragraph",
            "value": file_name,
            "value_type": "text",
            "position": {"page": 1, "paragraph_index": 0},
        },
        {
            "id": "body",
            "type": "paragraph",
            "value": "Reported 42 people in the article body.",
            "value_type": "text",
            "position": {"page": 1, "paragraph_index": 1},
        },
    ]

    claims = collect_raw_claims(raw_payload)

    assert "num:42" in claims
    assert "date:2026-06-08" not in claims
    assert "num:647" not in claims


def test_file_profile_ignores_markdown_frontmatter_header_for_numeric_claims():
    raw_payload = file_raw(content_hash="sha256:file-frontmatter-header", sections=[])
    raw_payload["ocr_reference"]["blocks"] = [
        {
            "id": "header_frontmatter",
            "type": "paragraph",
            "value": (
                "--- source_url: https://example.test/article-100.html "
                "source_domain: example.test title: Example published_at: 2026-06-08 "
                "fetched_at: 2026-06-13T10:00:00Z url_hash: cd66cb6db647 "
                "content_hash: sha256:abc extractor: fallback-html raw_html_path: raw.html ---"
            ),
            "value_type": "text",
            "position": {"page": 1, "paragraph_index": 0},
        },
        {
            "id": "body",
            "type": "paragraph",
            "value": "Reported 42 people in the article body.",
            "value_type": "text",
            "position": {"page": 1, "paragraph_index": 1},
        },
    ]

    claims = collect_raw_claims(raw_payload)

    assert "num:42" in claims
    assert "date:2026-06-08" not in claims
    assert "date:2026-06-13" not in claims
    assert "num:647" not in claims


def test_file_profile_table_cell_claim_paths_stay_on_raw_blocks():
    raw_payload = file_raw(
        content_hash="sha256:file-table-cell",
        sections=[],
        tables=[{"page": 1, "rows": [["50,90 EUR"]]}],
    )

    claims = collect_raw_claims(raw_payload)
    pages = compact_pages_from_payload(raw_payload)

    assert claims["num:50.9"].field_paths == {"ocr_reference.blocks[0].value"}
    assert pages == [{"page": 1, "blocks": ["50,90 EUR"]}]


def test_file_profile_splits_layout_lines_before_numeric_claim_parsing():
    raw_payload = file_raw(
        content_hash="sha256:file-layout-lines",
        sections=["38\nCote de Blaye\n20\n210.8"],
    )

    claims = collect_raw_claims(raw_payload)

    assert "num:20210.8" not in claims
    assert "num:38" in claims
    assert "num:20" in claims
    assert "num:210.8" in claims


def test_file_profile_keeps_space_grouped_numbers_inside_one_line():
    raw_payload = file_raw(
        content_hash="sha256:file-space-grouped-number",
        sections=["Total 1 234,56 EUR"],
    )

    claims = collect_raw_claims(raw_payload)

    assert "num:1234.56" in claims


def test_file_profile_does_not_collect_html_table_layout_numbers_as_claims():
    raw_payload = file_raw(
        content_hash="sha256:file-html-table-layout",
        sections=[
            (
                '<table><tr><td rowspan="3">4 x</td><td>Room 104</td>'
                '<td rowspan="3">65,00 EUR</td><td rowspan="3">260,00 EUR</td></tr></table>'
            )
        ],
    )

    claims = collect_raw_claims(raw_payload)

    assert "num:3" not in claims
    assert "num:4" in claims
    assert "num:260" in claims


def test_file_profile_keeps_zero_percent_tax_rates_strong():
    raw_payload = file_raw(
        content_hash="sha256:file-zero-tax-rate",
        sections=["USt.0%"],
    )

    claims = collect_raw_claims(raw_payload)

    assert claims["num:0"].strength == "strong"
