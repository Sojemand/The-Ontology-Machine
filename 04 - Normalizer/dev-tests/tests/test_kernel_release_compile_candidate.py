from __future__ import annotations

import json

from .kernel_release_materialization_support import MODULE_ROOT, _owner_request, dispatch

def test_compile_semantic_release_candidate_uses_neutral_custom_version(tmp_path: Path) -> None:
    result = dispatch(
        "compile_semantic_release_candidate",
        _owner_request(
            "compile_semantic_release_candidate",
            taxonomy_ref={"taxonomy_id": "normalizer_taxonomy.master", "taxonomy_fingerprint": "tax-fp", "runtime_locale": "en"},
            projection_refs=[{"projection_id": "finance.receipts.v1", "projection_fingerprint": "proj-fp"}],
            semantic_release_folder=str(tmp_path / "Semantic Release"),
            runtime_locale="en",
        ),
        project_root=MODULE_ROOT,
    )

    assert result["status"] == "ok"
    release_ref = result["output_refs"]["release_ref"]
    assert release_ref["release_version"] == "custom.v1"
    assert result["output_refs"]["semantic_release_version"] == "custom.v1"
    assert "phase19" not in json.dumps(result)
