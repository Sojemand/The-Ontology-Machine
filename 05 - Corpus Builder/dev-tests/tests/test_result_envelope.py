from __future__ import annotations

import json
from pathlib import Path

from corpus_builder.orchestrator_contract.result_envelope import build_result


def test_build_result_serializes_contract_detail_shapes() -> None:
    result = build_result(
        headline="Merge preflight",
        summary_lines=["ready"],
        detail={"document_ids": {"doc-b", "doc-a"}, "path": Path("corpus.db")},
        artifacts=[{"label": "Corpus DB", "value": Path("corpus.db")}],
    )

    json.dumps(result)
    assert result["detail"]["document_ids"] == ["doc-a", "doc-b"]
    assert result["detail"]["path"] == "corpus.db"
