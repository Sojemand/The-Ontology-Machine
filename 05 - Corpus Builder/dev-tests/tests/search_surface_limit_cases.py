from __future__ import annotations

from .search_surface_support import load_from_file
from corpus_builder.search import fulltext_search, hybrid_search


def test_non_positive_limits_are_clamped(
    db,
    vision_structured,
    vision_validation_report,
    make_input_pair,
):
    for index in range(3):
        structured = dict(vision_structured)
        structured["source"] = dict(vision_structured["source"])
        structured["source"]["file_path"] = f"C:/docs/fts-{index}.pdf"
        structured["source"]["content_hash"] = f"sha256:fts-{index}"
        assert load_from_file(
            db,
            make_input_pair(f"fts_limit_{index}", structured, vision_report=vision_validation_report),
        ).status == "loaded"

    assert len(fulltext_search(db, "Schlussrechnung", limit=0)) == 1
    assert len(fulltext_search(db, "Schlussrechnung", limit=-5)) == 1
    assert len(hybrid_search(db, "Schlussrechnung", top_k=0)) == 1
