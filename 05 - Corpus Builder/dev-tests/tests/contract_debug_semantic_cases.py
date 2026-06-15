from __future__ import annotations

from pathlib import Path

from .contract_debug_support import dispatch, loaded_semantic_corpus


def test_dispatch_semantic_audit_runs_against_real_corpus_db(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized) -> None:
    context, corpus_db_path = loaded_semantic_corpus(
        tmp_path,
        vision_structured=vision_structured,
        vision_validation_report=vision_validation_report,
        vision_normalized=vision_normalized,
    )

    response = dispatch(context, {"action": "semantic_audit", "corpus_db_path": str(corpus_db_path)})

    assert response["status"] == "ok"
    assert response["headline"] == "Semantic audit completed"
    assert response["detail"]["status"]["total_documents"] == 1
    assert response["detail"]["status"]["unknown_projection_documents"] == 0
    assert Path(response["detail"]["report_path"]).exists()


def test_dispatch_backfill_stale_runs_against_real_corpus_db(tmp_path: Path, vision_structured, vision_validation_report, vision_normalized) -> None:
    context, corpus_db_path = loaded_semantic_corpus(
        tmp_path,
        vision_structured=vision_structured,
        vision_validation_report=vision_validation_report,
        vision_normalized=vision_normalized,
    )

    response = dispatch(
        context,
        {
            "action": "backfill_stale",
            "corpus_db_path": str(corpus_db_path),
            "stale_only": False,
            "limit": 1,
        },
    )

    assert response["status"] == "ok"
    assert response["headline"] == "Semantic backfill completed"
    assert response["detail"]["processed_count"] == 1
    assert response["detail"]["error_count"] == 0
