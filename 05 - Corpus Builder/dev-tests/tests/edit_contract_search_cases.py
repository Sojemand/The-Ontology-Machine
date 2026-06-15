from __future__ import annotations

import json
from pathlib import Path

from .edit_contract_support import _copy_module, _invoke_contract


def test_search_policy_roundtrip_and_removed_semantic_release_surface(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    search_response = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.search_policy",
            "value": {
                "fulltext.limit_default": 30,
                "semantic.top_k_default": 12,
                "hybrid.top_k_default": 8,
                "hybrid.candidate_multiplier": 3,
                "hybrid.fts_weight": 0.25,
                "hybrid.vec_weight": 0.75,
                "readonly.max_rows": 40,
                "fts.normalize_by_max_score": False,
            },
        },
    )

    search_policy = json.loads((module_root / "config" / "search_policy.json").read_text(encoding="utf-8"))
    removed_read = _invoke_contract(
        module_root,
        tmp_path,
        {"action": "read_surface", "surface_id": "corpus_builder.semantic_release_default"},
    )
    removed_write = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.semantic_release_default",
            "value": {"release_id": "semantic_release.default"},
        },
    )

    assert search_response["status"] == "ok"
    assert search_response["value"] == {
        "fulltext.limit_default": 30,
        "semantic.top_k_default": 12,
        "hybrid.top_k_default": 8,
        "hybrid.candidate_multiplier": 3,
        "hybrid.fts_weight": 0.25,
        "hybrid.vec_weight": 0.75,
        "readonly.max_rows": 40,
        "fts.normalize_by_max_score": False,
    }
    assert search_policy == {
        "fulltext": {"limit_default": 30},
        "semantic": {"top_k_default": 12},
        "hybrid": {
            "top_k_default": 8,
            "candidate_multiplier": 3,
            "fts_weight": 0.25,
            "vec_weight": 0.75,
        },
        "readonly": {"max_rows": 40},
        "fts": {"normalize_by_max_score": False},
    }
    assert removed_read["status"] == "error"
    assert "Unbekannte Surface" in removed_read["reason"]
    assert removed_write["status"] == "error"
    assert "Unbekannte Surface" in removed_write["reason"]


def test_debug_capabilities_is_no_longer_exposed_as_surface(tmp_path: Path) -> None:
    module_root = _copy_module(tmp_path)

    response = _invoke_contract(
        module_root,
        tmp_path,
        {
            "action": "write_surface",
            "surface_id": "corpus_builder.debug_capabilities",
            "value": {"module_key": "override"},
        },
    )

    assert response["status"] == "error"
    assert "Unbekannte Surface" in response["reason"]
